"""
Local Python image generation provider using Hugging Face Diffusers (SDXL, etc.).
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import ImageGenerationProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class DiffusersImageProvider(ImageGenerationProvider):
    """Local image generation provider using Hugging Face Diffusers."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._pipeline = None
        self._refiner = None
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
                ProviderCapability(name="generate", supported=True, description="Text-to-image"),
                ProviderCapability(name="generate_with_reference", supported=True, description="Image-to-image (IP-Adapter/ControlNet)"),
                ProviderCapability(name="inpaint", supported=True, description="Inpainting"),
                ProviderCapability(name="outpaint", supported=True, description="Outpainting"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the diffusion model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
            import torch
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            # Load base pipeline
            self._pipeline = StableDiffusionXLPipeline.from_pretrained(
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
                    pass  # xformers not available
            
            if self.config.enable_cpu_offload:
                self._pipeline.enable_model_cpu_offload()
            elif self.config.enable_sequential_cpu_offload:
                self._pipeline.enable_sequential_cpu_offload()
            
            # Load refiner if specified
            if self.config.refiner_path and Path(self.config.refiner_path).exists():
                self._refiner = StableDiffusionXLImg2ImgPipeline.from_pretrained(
                    self.config.refiner_path,
                    torch_dtype=getattr(torch, self.config.torch_dtype),
                    variant=self.config.variant,
                    use_safetensors=self.config.use_safetensors,
                ).to(self.config.device)
                
                if self.config.enable_xformers:
                    try:
                        self._refiner.enable_xformers_memory_efficient_attention()
                    except Exception:
                        pass
            
            # Load VAE if specified
            if self.config.vae_path and Path(self.config.vae_path).exists():
                from diffusers import AutoencoderKL
                vae = AutoencoderKL.from_pretrained(
                    self.config.vae_path,
                    torch_dtype=getattr(torch, self.config.torch_dtype),
                ).to(self.config.device)
                self._pipeline.vae = vae
                if self._refiner:
                    self._refiner.vae = vae
            
            # Set scheduler
            if self.config.scheduler:
                from diffusers import EulerAncestralDiscreteScheduler
                if self.config.scheduler == "euler_ancestral":
                    self._pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(
                        self._pipeline.scheduler.config
                    )
            
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
            raise RuntimeError(f"Failed to load image generation model: {str(e)}") from e
    
    async def unload(self) -> None:
        """Unload the model."""
        if not self._loaded:
            return
        
        try:
            if self._pipeline:
                del self._pipeline
            if self._refiner:
                del self._refiner
            
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._pipeline = None
            self._refiner = None
            self._loaded = False
            
            log_model_unload(None, self.metadata.model_name, "local_python:diffusers")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._pipeline is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate", supported=True, description="Text-to-image"),
            ProviderCapability(name="generate_with_reference", supported=True, description="Image-to-image"),
            ProviderCapability(name="inpaint", supported=True, description="Inpainting"),
            ProviderCapability(name="outpaint", supported=True, description="Outpainting"),
        ]
    
    async def _generate_image(
        self, 
        prompt: str, 
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
        seed: Optional[int],
        generator: Any,
        **kwargs
    ) -> Any:
        """Internal method to generate image."""
        import torch
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
                output_type="pil",
            )
        )
        
        return result.images[0]
    
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        """Generate image from text prompt."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            import torch
            
            # Get parameters
            width = kwargs.get("width", self.config.default_width)
            height = kwargs.get("height", self.config.default_height)
            steps = kwargs.get("steps", self.config.default_steps)
            guidance_scale = kwargs.get("guidance_scale", self.config.default_guidance_scale)
            seed = kwargs.get("seed")
            negative_prompt = kwargs.get("negative_prompt", "")
            
            # Create generator for reproducibility
            generator = torch.Generator(device=self.config.device).manual_seed(seed) if seed else None
            
            # Generate base image
            image = await self._generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                guidance_scale=guidance_scale,
                seed=seed,
                generator=generator,
            )
            
            # Refine if refiner available
            if self._refiner:
                image = await loop.run_in_executor(
                    None,
                    lambda: self._refiner(
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        image=image,
                        num_inference_steps=steps // 2,
                        guidance_scale=guidance_scale,
                        generator=generator,
                        output_type="pil",
                    ).images[0]
                )
            
            duration = time.time() - start_time
            
            log_generation(
                None,
                "image_generation",
                "local_python:diffusers",
                self.metadata.model_name,
                duration
            )
            
            return GenerationResult(
                success=True,
                data={
                    "image": image,  # PIL Image
                    "width": width,
                    "height": height,
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "seed": seed or (generator.initial_seed() if generator else None),
                    "steps": steps,
                    "guidance_scale": guidance_scale,
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
                error=f"Image generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def generate_with_reference(
        self, 
        prompt: str, 
        reference_image: str, 
        **kwargs
    ) -> GenerationResult:
        """Generate image with reference (image-to-image)."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            from PIL import Image
            import torch
            
            # Load reference image
            ref_img = Image.open(reference_image).convert("RGB")
            
            # Resize to target dimensions
            width = kwargs.get("width", self.config.default_width)
            height = kwargs.get("height", self.config.default_height)
            ref_img = ref_img.resize((width, height), Image.LANCZOS)
            
            # Get parameters
            steps = kwargs.get("steps", self.config.default_steps)
            guidance_scale = kwargs.get("guidance_scale", self.config.default_guidance_scale)
            strength = kwargs.get("strength", 0.8)
            seed = kwargs.get("seed")
            negative_prompt = kwargs.get("negative_prompt", "")
            
            generator = torch.Generator(device=self.config.device).manual_seed(seed) if seed else None
            
            # Run img2img
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    image=ref_img,
                    strength=strength,
                    num_inference_steps=steps,
                    guidance_scale=guidance_scale,
                    generator=generator,
                    output_type="pil",
                )
            )
            
            image = result.images[0]
            duration = time.time() - start_time
            
            log_generation(
                None,
                "image_to_image",
                "local_python:diffusers",
                self.metadata.model_name,
                duration
            )
            
            return GenerationResult(
                success=True,
                data={
                    "image": image,
                    "width": width,
                    "height": height,
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "seed": seed or (generator.initial_seed() if generator else None),
                    "reference_image": reference_image,
                    "strength": strength,
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
                error=f"Image-to-image generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def inpaint(self, image: str, mask: str, prompt: str, **kwargs) -> GenerationResult:
        """Inpaint image (not fully implemented for SDXL without ControlNet)."""
        return GenerationResult(
            success=False,
            error="Inpainting requires ControlNet pipeline, not implemented in base provider"
        )
    
    async def outpaint(self, image: str, prompt: str, **kwargs) -> GenerationResult:
        """Outpaint image (not implemented)."""
        return GenerationResult(
            success=False,
            error="Outpainting not implemented"
        )
    
    async def cancel(self) -> None:
        """Cancel ongoing generation."""
        pass