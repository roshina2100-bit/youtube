"""
Local Python SFX provider using Hugging Face Transformers (AudioLDM 2, AudioGen).
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import SoundEffectProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class TransformersSFXProvider(SoundEffectProvider):
    """Local SFX provider using Hugging Face Transformers (AudioLDM 2, AudioGen)."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._pipeline = None
        self._model_type = "audioldm2"  # or "audiogen"
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
                ProviderCapability(name="generate", supported=True, description="Text-to-SFX"),
                ProviderCapability(name="generate_variations", supported=True, description="Multiple variations"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the SFX generation model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            import torch
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            # Determine model type from path or config
            model_name_lower = str(model_path).lower()
            if "audiogen" in model_name_lower:
                self._model_type = "audiogen"
                from transformers import AutoProcessor, AutoModelForTextToWaveform
                self._processor = AutoProcessor.from_pretrained(model_path)
                self._model = AutoModelForTextToWaveform.from_pretrained(
                    model_path,
                    torch_dtype=getattr(torch, self.config.torch_dtype),
                ).to(self.config.device)
            else:
                # Default to AudioLDM 2
                self._model_type = "audioldm2"
                from diffusers import AudioLDM2Pipeline
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
                f"local_python:{'transformers' if self._model_type == 'audiogen' else 'diffusers'}",
                self.config.device
            )
            
        except ImportError:
            self._loaded = False
            raise RuntimeError("SFX dependencies not installed. Install with: pip install diffusers transformers accelerate")
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load SFX model: {str(e)}") from e
    
    async def unload(self) -> None:
        """Unload the model."""
        if not self._loaded:
            return
        
        try:
            if self._pipeline:
                del self._pipeline
            if hasattr(self, '_model') and self._model:
                del self._model
            if hasattr(self, '_processor') and self._processor:
                del self._processor
            
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._pipeline = None
            self._model = None
            self._processor = None
            self._loaded = False
            
            log_model_unload(None, self.metadata.model_name, f"local_python:{'transformers' if self._model_type == 'audiogen' else 'diffusers'}")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        if self._model_type == "audiogen":
            return self._loaded and self._model is not None
        return self._loaded and self._pipeline is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate", supported=True, description="Text-to-SFX"),
            ProviderCapability(name="generate_variations", supported=True, description="Multiple variations"),
        ]
    
    async def generate(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        """Generate sound effect from text prompt."""
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
            
            if self._model_type == "audiogen":
                return await self._generate_audiogen(prompt, duration, kwargs, start_time)
            else:
                return await self._generate_audioldm2(prompt, duration, kwargs, start_time)
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"SFX generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def _generate_audiogen(self, prompt: str, duration: float, kwargs: Dict, start_time: float) -> GenerationResult:
        """Generate using AudioGen."""
        import torch
        import scipy.io.wavfile
        import numpy as np
        
        # AudioGen generates at 16kHz
        sample_rate = 16000
        
        inputs = self._processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        ).to(self.config.device)
        
        # Calculate max tokens for duration
        max_new_tokens = int(duration * sample_rate / 256)  # Approximate
        
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
        
        output_path = kwargs.get("output_path", f"/tmp/sfx_output_{int(time.time())}.wav")
        scipy.io.wavfile.write(output_path, sample_rate, audio_values)
        
        duration_actual = time.time() - start_time
        
        log_generation(
            None,
            "sfx_generation",
            "local_python:transformers",
            self.metadata.model_name,
            duration_actual
        )
        
        return GenerationResult(
            success=True,
            data={
                "audio_path": output_path,
                "duration_seconds": len(audio_values) / sample_rate,
                "prompt": prompt,
                "sample_rate": sample_rate,
            },
            metadata={
                "model": self.metadata.model_name,
                "duration_seconds": duration_actual,
            },
            duration_seconds=duration_actual
        )
    
    async def _generate_audioldm2(self, prompt: str, duration: float, kwargs: Dict, start_time: float) -> GenerationResult:
        """Generate using AudioLDM 2."""
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
                audio_length_in_s=min(duration, self.config.max_duration),
                guidance_scale=kwargs.get("guidance_scale", 3.5),
                generator=torch.Generator(device=self.config.device).manual_seed(kwargs.get("seed", 42)),
            )
        )
        
        audio = result.audios[0]
        
        output_path = kwargs.get("output_path", f"/tmp/sfx_output_{int(time.time())}.wav")
        scipy.io.wavfile.write(output_path, sample_rate, audio)
        
        duration_actual = time.time() - start_time
        
        log_generation(
            None,
            "sfx_generation",
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
    
    async def generate_variations(self, prompt: str, duration: float, count: int, **kwargs) -> List[GenerationResult]:
        """Generate multiple variations of a sound effect."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return [GenerationResult(success=False, error="Model not loaded") for _ in range(count)]
        
        results = []
        for i in range(count):
            # Use different seed for each variation
            variation_kwargs = kwargs.copy()
            variation_kwargs["seed"] = kwargs.get("seed", 42) + i
            variation_kwargs["output_path"] = kwargs.get("output_path", f"/tmp/sfx_var_{i}_{int(time.time())}.wav")
            
            result = await self.generate(prompt, duration, **variation_kwargs)
            if result.success:
                result.data["variation"] = i + 1
            results.append(result)
        
        return results
    
    async def cancel(self) -> None:
        """Cancel ongoing generation."""
        pass