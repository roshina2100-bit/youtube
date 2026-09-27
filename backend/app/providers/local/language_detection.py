"""
Local Python language detection provider using fastText.
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import LanguageDetectionProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class FastTextLanguageDetectionProvider(LanguageDetectionProvider):
    """Local language detection provider using fastText."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._model = None
        self._loaded = False
        self._load_time = 0.0
        self._last_used = None
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="local_python",
            model_name=Path(self.config.model_path).name if self.config.model_path else "lid.176",
            version="1.0.0",
            capabilities=[
                ProviderCapability(name="detect_text", supported=True, description="Text language detection"),
                ProviderCapability(name="detect_audio", supported=False, description="Audio language detection (use transcription)"),
                ProviderCapability(name="detect_batch", supported=True, description="Batch detection"),
            ],
            loaded=self._loaded,
            device="cpu",
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the fastText model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            import fasttext
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                # Try default locations
                default_paths = [
                    "C:/Models/lid.176.bin",
                    "C:/Models/lid.176.ftz",
                    "/models/lid.176.bin",
                    "./models/lid.176.bin",
                ]
                for p in default_paths:
                    if Path(p).exists():
                        model_path = p
                        break
                else:
                    raise ValueError(f"fastText model not found. Tried: {model_path} and defaults")
            
            self._model = fasttext.load_model(model_path)
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._last_used = time.time()
            
            log_model_load(
                None,
                self.metadata.model_name,
                "local_python:fasttext",
                "cpu"
            )
            
        except ImportError:
            self._loaded = False
            raise RuntimeError("fasttext not installed. Install with: pip install fasttext")
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load language detection model: {str(e)}") from e
    
    async def unload(self) -> None:
        """Unload the model."""
        if not self._loaded:
            return
        
        try:
            self._model = None
            self._loaded = False
            
            log_model_unload(None, self.metadata.model_name, "local_python:fasttext")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._model is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="detect_text", supported=True, description="Text language detection"),
            ProviderCapability(name="detect_audio", supported=False, description="Audio language detection"),
            ProviderCapability(name="detect_batch", supported=True, description="Batch detection"),
        ]
    
    def _parse_predictions(self, labels: List[str], probs: List[float], k: int) -> List[Dict[str, Any]]:
        """Parse fastText predictions."""
        results = []
        for label, prob in zip(labels[:k], probs[:k]):
            # fastText labels are like "__label__en"
            lang_code = label.replace("__label__", "")
            results.append({
                "language": lang_code,
                "confidence": float(prob),
            })
        return results
    
    async def detect_text(self, text: str, **kwargs) -> GenerationResult:
        """Detect language from text."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            # Clean text
            clean_text = text.replace("\n", " ").strip()
            if not clean_text:
                return GenerationResult(
                    success=False,
                    error="Empty text provided",
                    duration_seconds=time.time() - start_time
                )
            
            # Run detection in thread pool
            loop = asyncio.get_event_loop()
            k = kwargs.get("top_k", 5)
            labels, probs = await loop.run_in_executor(
                None,
                lambda: self._model.predict(clean_text, k=k)
            )
            
            alternatives = self._parse_predictions(labels, probs, k)
            
            duration = time.time() - start_time
            
            log_generation(
                None,
                "language_detection",
                "local_python:fasttext",
                self.metadata.model_name,
                duration
            )
            
            return GenerationResult(
                success=True,
                data={
                    "language": alternatives[0]["language"] if alternatives else "unknown",
                    "confidence": alternatives[0]["confidence"] if alternatives else 0.0,
                    "alternatives": alternatives[1:],
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
                error=f"Language detection failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def detect_audio(self, audio_path: str, **kwargs) -> GenerationResult:
        """Detect language from audio (not directly supported, use transcription)."""
        return GenerationResult(
            success=False,
            error="Audio language detection not supported directly. Use transcription provider first."
        )
    
    async def cancel(self) -> None:
        """Cancel ongoing detection."""
        pass