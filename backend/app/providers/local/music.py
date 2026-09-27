"""
Local Python music generation provider using Hugging Face Transformers (MusicGen, AudioLDM).
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import MusicGenerationProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class TransformersMusicProvider(MusicGenerationProvider):
    """Local music generation provider using Hugging Face Transformers (MusicGen)."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._model = None
        self._processor = None
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
                ProviderCapability(name="generate", supported=True, description="Text-to-music"),
                ProviderCapability(name="generate_with_melody", supported=True, description="Melody-conditioned generation"),
                ProviderCapability(name="continue", supported=True, description="Continue existing music"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the music generation model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            from transformers import AutoProcessor, MusicgenForConditionalGeneration
            import torch
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            self._processor = AutoProcessor.from_pretrained(model_path)
            self._model = MusicgenForConditionalGeneration.from_pretrained(
                model_path,
                torch_dtype=getattr(torch, self.config.torch_dtype),
            ).to(self.config.device)
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._last_used = time.time()
            
            log_model_load(
                None,
                self.metadata.model_name,
                "local_python:transformers",
                self.config.device
            )
            
        except ImportError:
            self._loaded = False
            raise RuntimeError("MusicGen dependencies not installed. Install with: pip install transformers accelerate")
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load music generation model: {str(e)}") from e
    
    async def unload(self) -> None:
        """Unload the model."""
        if not self._loaded:
            return
        
        try:
            if self._model:
                del self._model
            if self._processor:
                del self._processor
            
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._model = None
            self._processor = None
            self._loaded = False
            
            log_model_unload(None, self.metadata.model_name, "local_python:transformers")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._model is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate", supported=True, description="Text-to-music"),
            ProviderCapability(name="generate_with_melody", supported=True, description="Melody-conditioned"),
            ProviderCapability(name="continue", supported=True, description="Continue music"),
        ]
    
    async def generate(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        """Generate music from text prompt."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            import torch
            import scipy.io.wavfile
            import numpy as np
            
            # MusicGen generates at 32kHz
            sample_rate = 32000
            max_new_tokens = int(duration * sample_rate / self._model.config.audio_encoder.frame_rate)
            
            # Prepare inputs
            inputs = self._processor(
                text=[prompt],
                padding=True,
                return_tensors="pt",
            ).to(self.config.device)
            
            # Generation config
            generation_config = {
                "max_new_tokens": min(max_new_tokens, self._model.config.max_length),
                "do_sample": kwargs.get("do_sample", True),
                "temperature": kwargs.get("temperature", 1.0),
                "top_k": kwargs.get("top_k", 250),
                "top_p": kwargs.get("top_p", 0.0),
                "guidance_scale": kwargs.get("guidance_scale", 3.0),
            }
            
            # Run generation
            loop = asyncio.get_event_loop()
            audio_values = await loop.run_in_executor(
                None,
                lambda: self._model.generate(**inputs, **generation_config)
            )
            
            # Convert to numpy
            audio_values = audio_values[0].cpu().numpy()
            
            # Save to file
            output_path = kwargs.get("output_path", f"/tmp/music_output_{int(time.time())}.wav")
            scipy.io.wavfile.write(output_path, sample_rate, audio_values.T)
            
            duration_actual = time.time() - start_time
            
            log_generation(
                None,
                "music_generation",
                "local_python:transformers",
                self.metadata.model_name,
                duration_actual
            )
            
            return GenerationResult(
                success=True,
                data={
                    "audio_path": output_path,
                    "duration_seconds": len(audio_values[0]) / sample_rate,
                    "prompt": prompt,
                    "sample_rate": sample_rate,
                },
                metadata={
                    "model": self.metadata.model_name,
                    "duration_seconds": duration_actual,
                },
                duration_seconds=duration_actual
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Music generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def generate_with_melody(self, prompt: str, melody_path: str, **kwargs) -> GenerationResult:
        """Generate music conditioned on melody."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            import torch
            import torchaudio
            import scipy.io.wavfile
            import numpy as np
            
            # Load melody
            melody, sr = torchaudio.load(melody_path)
            if melody.shape[0] > 1:
                melody = melody.mean(dim=0, keepdim=True)
            
            # Resample to 32kHz if needed
            if sr != 32000:
                resampler = torchaudio.transforms.Resample(sr, 32000)
                melody = resampler(melody)
            
            duration = kwargs.get("duration", 30.0)
            sample_rate = 32000
            max_new_tokens = int(duration * sample_rate / self._model.config.audio_encoder.frame_rate)
            
            # Prepare inputs with melody
            inputs = self._processor(
                text=[prompt],
                audio=melody,
                padding=True,
                return_tensors="pt",
            ).to(self.config.device)
            
            generation_config = {
                "max_new_tokens": min(max_new_tokens, self._model.config.max_length),
                "do_sample": kwargs.get("do_sample", True),
                "temperature": kwargs.get("temperature", 1.0),
                "top_k": kwargs.get("top_k", 250),
                "guidance_scale": kwargs.get("guidance_scale", 3.0),
            }
            
            loop = asyncio.get_event_loop()
            audio_values = await loop.run_in_executor(
                None,
                lambda: self._model.generate(**inputs, **generation_config)
            )
            
            audio_values = audio_values[0].cpu().numpy()
            
            output_path = kwargs.get("output_path", f"/tmp/music_melody_{int(time.time())}.wav")
            scipy.io.wavfile.write(output_path, sample_rate, audio_values.T)
            
            duration_actual = time.time() - start_time
            
            log_generation(
                None,
                "music_generation_melody",
                "local_python:transformers",
                self.metadata.model_name,
                duration_actual
            )
            
            return GenerationResult(
                success=True,
                data={
                    "audio_path": output_path,
                    "duration_seconds": len(audio_values[0]) / sample_rate,
                    "prompt": prompt,
                    "melody_path": melody_path,
                    "sample_rate": sample_rate,
                },
                metadata={
                    "model": self.metadata.model_name,
                    "duration_seconds": duration_actual,
                },
                duration_seconds=duration_actual
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Melody-conditioned music generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def continue_music(self, audio_path: str, duration: float, **kwargs) -> GenerationResult:
        """Continue existing music (not directly supported by MusicGen)."""
        # MusicGen doesn't natively support continuation
        # Could use the last few seconds as melody conditioning
        return GenerationResult(
            success=False,
            error="Music continuation not directly supported. Use generate_with_melody with the end of the track as melody."
        )
    
    async def cancel(self) -> None:
        """Cancel ongoing generation."""
        pass


class AudioLDMMusicProvider(MusicGenerationProvider):
    """Local music generation provider using AudioLDM 2."""
    
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
                ProviderCapability(name="generate", supported=True, description="Text-to-music"),
                ProviderCapability(name="generate_with_melody", supported=False, description="Melody-conditioned (not supported)"),
                ProviderCapability(name="continue", supported=False, description="Continue music (not supported)"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the AudioLDM model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            from diffusers import AudioLDM2Pipeline
            import torch
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            self._pipeline = AudioLDM2Pipeline.from_pretrained(
                model_path,
                torch_dtype=getattr(torch, self.config.torch_dtype),
            ).to(self.config.device)
            
            if self.config.enable_xformers:
                try:
                    self._pipeline.enable_xformers_memory_efficient_attention()
                except Exception:
                    pass
            
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
            raise RuntimeError("AudioLDM dependencies not installed. Install with: pip install diffusers accelerate")
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load AudioLDM model: {str(e)}") from e
    
    async def unload(self) -> None:
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
            ProviderCapability(name="generate", supported=True, description="Text-to-music"),
            ProviderCapability(name="generate_with_melody", supported=False, description="Melody-conditioned"),
            ProviderCapability(name="continue", supported=False, description="Continue music"),
        ]
    
    async def generate(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            import torch
            import scipy.io.wavfile
            import numpy as np
            
            # AudioLDM2 generates at 16kHz
            sample_rate = 16000
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._pipeline(
                    prompt=prompt,
                    num_inference_steps=kwargs.get("steps", 50),
                    audio_length_in_s=duration,
                    guidance_scale=kwargs.get("guidance_scale", 3.5),
                    generator=torch.Generator(device=self.config.device).manual_seed(kwargs.get("seed", 42)),
                )
            )
            
            audio = result.audios[0]
            
            output_path = kwargs.get("output_path", f"/tmp/audioldm_music_{int(time.time())}.wav")
            scipy.io.wavfile.write(output_path, sample_rate, audio)
            
            duration_actual = time.time() - start_time
            
            log_generation(
                None,
                "music_generation",
                "local_python:diffusers",
                self.metadata.model_name,
                duration_actual
            )
            
            return GenerationResult(
                success=True,
                data={
                    "audio_path": output_path,
                    "duration_seconds": duration,
                    "prompt": prompt,
                    "sample_rate": sample_rate,
                },
                metadata={
                    "model": self.metadata.model_name,
                    "duration_seconds": duration_actual,
                },
                duration_seconds=duration_actual
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"AudioLDM music generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def generate_with_melody(self, prompt: str, melody_path: str, **kwargs) -> GenerationResult:
        return GenerationResult(
            success=False,
            error="Melody-conditioned generation not supported by AudioLDM 2"
        )
    
    async def continue_music(self, audio_path: str, duration: float, **kwargs) -> GenerationResult:
        return GenerationResult(
            success=False,
            error="Music continuation not supported by AudioLDM 2"
        )
    
    async def cancel(self) -> None:
        pass