"""
Local Python video generation provider using Hugging Face Diffusers (SVD, etc.).
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import VideoGenerationProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class DiffusersVideoProvider(VideoGenerationProvider):
    """Local video generation provider using Hugging Face Diffusers (SVD)."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._pipeline = None
        self._loaded = False
        self._load_time = 0.0
        self._last_used = None
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="local_python",
            model_name=Path(self.config.model_path).name if self.config.model_path else "unknown",
            version="1.0.0",
            capabilities=[
                ProviderCapability(name="generate", supported=True, description="Image-to-video"),
                ProviderCapability(name="generate_text_to_video", supported=False, description="Text-to-video (not supported by SVD)"),
                ProviderCapability(name="interpolate", supported=False, description="Frame interpolation"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the video diffusion model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            from diffusers import StableVideoDiffusionPipeline
            import torch
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            self._pipeline = StableVideoDiffusionPipeline.from_pretrained(
                model_path,
                torch_dtype=getattr(torch, self.config.torch_dtype),
                variant=self.config.variant,
                use_safetensors=self.config.use_safetensors,
            ).to(self.config.device)
            
            # Enable optimizations
            if self.config.enable_xformers:
                try:
                    self._pipeline.enable_xformers_memory_efficient_attention()
                except Exception:
                    pass
            
            if self.config.enable_cpu_offload:
                self._pipeline.enable_model_cpu_offload()
            elif self.config.enable_sequential_cpu_offload:
                self._pipeline.enable_sequential_cpu_offload()
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._last_used = time.time()
            
            log_model_load(
                None,
                self.metadata.model_name,
                "local_python:diffusers",
                self.config.device
            )
            
        except ImportError:
            self._loaded = False
            raise RuntimeError("diffusers not installed. Install with: pip install diffusers accelerate")
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load video generation model: {str(e)}") from e
    
    async def unload(self) -> None:
        """Unload the model."""
        if not self._loaded:
            return
        
        try:
            if self._pipeline:
                del self._pipeline
            
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._pipeline = None
            self._loaded = False
            
            log_model_unload(None, self.metadata.model_name, "local_python:diffusers")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._pipeline is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate", supported=True, description="Image-to-video"),
            ProviderCapability(name="generate_text_to_video", supported=False, description="Text-to-video"),
            ProviderCapability(name="interpolate", supported=False, description="Frame interpolation"),
        ]
    
    async def generate(self, image_path: str, prompt: str, **kwargs) -> GenerationResult:
        """Generate video from image (image-to-video)."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            from PIL import Image
            import torch
            import numpy as np
            
            # Load and prepare image
            image = Image.open(image_path).convert("RGB")
            
            # SVD expects specific resolution (typically 1024x576 or 576x1024)
            target_width = kwargs.get("width", 1024)
            target_height = kwargs.get("height", 576)
            image = image.resize((target_width, target_height), Image.LANCZOS)
            
            # Get parameters
            num_frames = kwargs.get("num_frames", self.config.num_frames)
            fps = kwargs.get("fps", self.config.fps)
            motion_bucket_id = kwargs.get("motion_bucket_id", self.config.motion_bucket_id)
            noise_aug_strength = kwargs.get("noise_aug_strength", self.config.noise_aug_strength)
            decode_chunk_size = kwargs.get("decode_chunk_size", self.config.decode_chunk_size)
            seed = kwargs.get("seed")
            
            generator = torch.Generator(device=self.config.device).manual_seed(seed) if seed else None
            
            # Run video generation
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._pipeline(
                    image=image,
                    num_frames=num_frames,
                    fps=fps,
                    motion_bucket_id=motion_bucket_id,
                    noise_aug_strength=noise_aug_strength,
                    decode_chunk_size=decode_chunk_size,
                    generator=generator,
                    output_type="pil",
                )
            )
            
            frames = result.frames[0]  # List of PIL images
            
            duration = time.time() - start_time
            
            log_generation(
                None,
                "video_generation",
                "local_python:diffusers",
                self.metadata.model_name,
                duration
            )
            
            return GenerationResult(
                success=True,
                data={
                    "frames": frames,  # List of PIL Images
                    "num_frames": len(frames),
                    "fps": fps,
                    "duration_seconds": len(frames) / fps,
                    "width": target_width,
                    "height": target_height,
                    "prompt": prompt,
                    "seed": seed or (generator.initial_seed() if generator else None),
                    "motion_bucket_id": motion_bucket_id,
                },
                metadata={
                    "model": self.metadata.model_name,
                    "duration_seconds": duration,
                },
                duration_seconds=duration
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Video generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def generate_text_to_video(self, prompt: str, **kwargs) -> GenerationResult:
        """Generate video from text (not supported by SVD)."""
        return GenerationResult(
            success=False,
            error="Text-to-video not supported by Stable Video Diffusion. Use image-to-video instead."
        )
    
    async def interpolate(self, frames: List[str], **kwargs) -> GenerationResult:
        """Interpolate between frames (not implemented)."""
        return GenerationResult(
            success=False,
            error="Frame interpolation not implemented"
        )
    
    async def cancel(self) -> None:
        """Cancel ongoing generation."""
        pass


class FFmpegVideoFallback:
    """FFmpeg-based deterministic video generation fallback.
    
    Provides basic camera movements (zoom, pan, parallax) when 
    true generative video models are unavailable.
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
    
    async def generate_zoom_pan(
        self,
        image_path: str,
        output_path: str,
        duration: float = 5.0,
        fps: int = 30,
        zoom_factor: float = 1.1,
        pan_direction: str = "center",  # center, left_to_right, right_to_left, top_to_bottom, bottom_to_top
        **kwargs
    ) -> GenerationResult:
        """Generate video with zoom and pan effect."""
        import subprocess
        
        start_time = time.time()
        
        try:
            # Build filter complex for zoom/pan
            # This creates a smooth zoom and pan effect
            w = "iw"
            h = "ih"
            
            if pan_direction == "center":
                # Slow zoom in to center
                filter_str = (
                    f"zoompan=z='min(zoom+0.0015,{zoom_factor})':"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    f"d={int(duration*fps)}:s={w}x{h}:fps={fps}"
                )
            elif pan_direction == "left_to_right":
                filter_str = (
                    f"zoompan=z='{zoom_factor}':"
                    f"x='(iw-iw/zoom)*t/{duration}':y='ih/2-(ih/zoom/2)':"
                    f"d={int(duration*fps)}:s={w}x{h}:fps={fps}"
                )
            elif pan_direction == "right_to_left":
                filter_str = (
                    f"zoompan=z='{zoom_factor}':"
                    f"x='(iw-iw/zoom)*(1-t/{duration})':y='ih/2-(ih/zoom/2)':"
                    f"d={int(duration*fps)}:s={w}x{h}:fps={fps}"
                )
            else:
                filter_str = (
                    f"zoompan=z='min(zoom+0.0015,{zoom_factor})':"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    f"d={int(duration*fps)}:s={w}x{h}:fps={fps}"
                )
            
            cmd = [
                self.ffmpeg_path,
                "-y",  # Overwrite output
                "-loop", "1",
                "-i", image_path,
                "-vf", filter_str,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-t", str(duration),
                "-r", str(fps),
                output_path
            ]
            
            # Run FFmpeg
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            )
            
            if result.returncode != 0:
                return GenerationResult(
                    success=False,
                    error=f"FFmpeg failed: {result.stderr}",
                    duration_seconds=time.time() - start_time
                )
            
            duration_actual = time.time() - start_time
            
            return GenerationResult(
                success=True,
                data={
                    "video_path": output_path,
                    "duration_seconds": duration,
                    "fps": fps,
                    "width": target_width,
                    "height": target_height,
                    "effect": f"zoom_pan_{pan_direction}",
                },
                metadata={
                    "method": "ffmpeg_fallback",
                    "duration_seconds": duration_actual,
                },
                duration_seconds=duration_actual
            )
            
        except subprocess.TimeoutExpired:
            return GenerationResult(
                success=False,
                error="FFmpeg timeout",
                duration_seconds=time.time() - start_time
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"FFmpeg fallback failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def generate_ken_burns(
        self,
        image_path: str,
        output_path: str,
        duration: float = 5.0,
        fps: int = 30,
        **kwargs
    ) -> GenerationResult:
        """Generate Ken Burns effect (slow zoom + pan)."""
        return await self.generate_zoom_pan(
            image_path, output_path, duration, fps,
            zoom_factor=1.2,
            pan_direction="center",
            **kwargs
        )
    
    async def concat_videos(
        self,
        video_paths: List[str],
        output_path: str,
        **kwargs
    ) -> GenerationResult:
        """Concatenate multiple videos."""
        import subprocess
        
        start_time = time.time()
        
        try:
            # Create concat file
            concat_file = Path(output_path).with_suffix(".txt")
            with open(concat_file, "w") as f:
                for vp in video_paths:
                    f.write(f"file '{vp}'\n")
            
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                output_path
            ]
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            )
            
            # Clean up concat file
            concat_file.unlink(missing_ok=True)
            
            if result.returncode != 0:
                return GenerationResult(
                    success=False,
                    error=f"FFmpeg concat failed: {result.stderr}",
                    duration_seconds=time.time() - start_time
                )
            
            return GenerationResult(
                success=True,
                data={"video_path": output_path},
                metadata={"method": "ffmpeg_concat"},
                duration_seconds=time.time() - start_time
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Video concat failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )