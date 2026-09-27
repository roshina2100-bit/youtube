"""
Local Python TTS provider using Hugging Face Transformers (XTTS, VITS, etc.).
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import TTSProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class TransformersTTSProvider(TTSProvider):
    """Local TTS provider using Hugging Face Transformers (XTTS v2, VITS, etc.)."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._model = None
        self._loaded = False
        self._load_time = 0.0
        self._last_used = None
        self._speaker_embeddings = {}
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="local_python",
            model_name=Path(self.config.model_path).name if self.config.model_path else "unknown",
            version="1.0.0",
            capabilities=[
                ProviderCapability(name="synthesize", supported=True, description="Text-to-speech"),
                ProviderCapability(name="synthesize_stream", supported=True, description="Streaming TTS"),
                ProviderCapability(name="clone_voice", supported=True, description="Voice cloning"),
                ProviderCapability(name="list_voices", supported=True, description="List voices"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the TTS model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            # Try to load XTTS v2 first (most capable)
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            # Check if it's XTTS or VITS based on model structure
            config_file = Path(model_path) / "config.json"
            if config_file.exists():
                import json
                with open(config_file) as f:
                    model_config = json.load(f)
                
                model_type = model_config.get("model_type", "").lower()
                
                if "xtts" in model_type or "xtts" in str(model_path).lower():
                    await self._load_xtts(model_path)
                elif "vits" in model_type:
                    await self._load_vits(model_path)
                else:
                    # Try generic transformers TTS
                    await self._load_generic_tts(model_path)
            else:
                # Try XTTS as default
                await self._load_xtts(model_path)
            
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
            raise RuntimeError("TTS dependencies not installed. Install with: pip install TTS transformers")
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load TTS model: {str(e)}") from e
    
    async def _load_xtts(self, model_path: str) -> None:
        """Load XTTS v2 model."""
        from TTS.api import TTS
        import torch
        
        self._model = TTS(model_path).to(self.config.device)
    
    async def _load_vits(self, model_path: str) -> None:
        """Load VITS model."""
        from TTS.api import TTS
        import torch
        
        self._model = TTS(model_path).to(self.config.device)
    
    async def _load_generic_tts(self, model_path: str) -> None:
        """Load generic transformers TTS model."""
        from transformers import AutoModel, AutoTokenizer
        import torch
        
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._model = AutoModel.from_pretrained(
            model_path,
            torch_dtype=getattr(torch, self.config.torch_dtype),
        ).to(self.config.device)
    
    async def unload(self) -> None:
        """Unload the model."""
        if not self._loaded:
            return
        
        try:
            if self._model:
                del self._model
            if hasattr(self, '_tokenizer') and self._tokenizer:
                del self._tokenizer
            
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._model = None
            self._loaded = False
            
            log_model_unload(None, self.metadata.model_name, "local_python:transformers")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._model is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="synthesize", supported=True, description="Text-to-speech"),
            ProviderCapability(name="synthesize_stream", supported=True, description="Streaming TTS"),
            ProviderCapability(name="clone_voice", supported=True, description="Voice cloning"),
            ProviderCapability(name="list_voices", supported=True, description="List voices"),
        ]
    
    async def synthesize(self, text: str, voice_id: str, **kwargs) -> GenerationResult:
        """Synthesize speech from text."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            language = kwargs.get("language", self.config.language)
            speed = kwargs.get("speed", self.config.speed)
            speaker_wav = kwargs.get("speaker_wav", self.config.speaker_wav)
            
            # Handle voice_id - could be a speaker name or path to reference audio
            if voice_id and Path(voice_id).exists():
                speaker_wav = voice_id
            
            # Run synthesis in thread pool
            loop = asyncio.get_event_loop()
            
            if hasattr(self._model, 'tts_to_file'):
                # Coqui TTS API
                output_path = kwargs.get("output_path", f"/tmp/tts_output_{int(time.time())}.wav")
                
                await loop.run_in_executor(
                    None,
                    lambda: self._model.tts_to_file(
                        text=text,
                        file_path=output_path,
                        speaker_wav=speaker_wav,
                        language=language,
                        speed=speed,
                    )
                )
                
                duration = time.time() - start_time
                
                log_generation(
                    None,
                    "tts_synthesis",
                    "local_python:transformers",
                    self.metadata.model_name,
                    duration
                )
                
                return GenerationResult(
                    success=True,
                    data={
                        "audio_path": output_path,
                        "text": text,
                        "voice_id": voice_id,
                        "language": language,
                        "speed": speed,
                    },
                    metadata={
                        "model": self.metadata.model_name,
                        "duration_seconds": duration,
                    },
                    duration_seconds=duration
                )
            else:
                # Generic transformers model
                return GenerationResult(
                    success=False,
                    error="Generic transformers TTS not fully implemented"
                )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"TTS synthesis failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def synthesize_stream(self, text: str, voice_id: str, **kwargs) -> AsyncIterator[bytes]:
        """Stream speech synthesis (not fully implemented for all models)."""
        # For now, synthesize full and yield in chunks
        result = await self.synthesize(text, voice_id, **kwargs)
        if result.success and result.data.get("audio_path"):
            import wave
            with wave.open(result.data["audio_path"], "rb") as wf:
                chunk_size = 1024
                data = wf.readframes(chunk_size)
                while data:
                    yield data
                    await asyncio.sleep(0.01)
                    data = wf.readframes(chunk_size)
    
    async def clone_voice(self, reference_audio: str, **kwargs) -> GenerationResult:
        """Clone voice from reference audio."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        
        try:
            # For XTTS, voice cloning is done by providing speaker_wav
            # The model computes speaker embedding internally
            voice_id = f"cloned_{Path(reference_audio).stem}_{int(time.time())}"
            
            # Store reference for later use
            self._speaker_embeddings[voice_id] = reference_audio
            
            return GenerationResult(
                success=True,
                data={
                    "voice_id": voice_id,
                    "reference_audio": reference_audio,
                },
                metadata={
                    "model": self.metadata.model_name,
                    "duration_seconds": time.time() - start_time,
                },
                duration_seconds=time.time() - start_time
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Voice cloning failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def list_voices(self) -> GenerationResult:
        """List available voices."""
        # For XTTS, voices are determined by reference audio files
        # Return built-in speakers if available
        voices = [
            {"id": "default", "name": "Default Speaker", "language": "en"},
        ]
        
        # Add any cloned voices
        for vid, ref in self._speaker_embeddings.items():
            voices.append({
                "id": vid,
                "name": f"Cloned: {Path(ref).name}",
                "language": "multi",
                "cloned": True,
            })
        
        return GenerationResult(
            success=True,
            data={"voices": voices}
        )
    
    async def cancel(self) -> None:
        """Cancel ongoing synthesis."""
        pass