"""
Local Python transcription provider using faster-whisper.
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import TranscriptionProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class FasterWhisperTranscriptionProvider(TranscriptionProvider):
    """Local transcription provider using faster-whisper."""
    
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
            model_name=Path(self.config.model_path).name if self.config.model_path else "unknown",
            version="1.0.0",
            capabilities=[
                ProviderCapability(name="transcribe", supported=True, description="Audio transcription"),
                ProviderCapability(name="transcribe_stream", supported=False, description="Streaming transcription (not implemented)"),
                ProviderCapability(name="diarize", supported=True, description="Speaker diarization"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the Whisper model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            from faster_whisper import WhisperModel
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            self._model = WhisperModel(
                model_path,
                device=self.config.device,
                compute_type=self.config.compute_type,
                cpu_threads=self.config.cpu_threads,
                num_workers=self.config.num_workers,
                download_root=self.config.download_root,
            )
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._last_used = time.time()
            
            log_model_load(
                None,
                self.metadata.model_name,
                "local_python:faster_whisper",
                self.config.device
            )
            
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load transcription model: {str(e)}") from e
    
    async def unload(self) -> None:
        """Unload the model."""
        if not self._loaded:
            return
        
        try:
            if self._model:
                del self._model
            
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._model = None
            self._loaded = False
            
            log_model_unload(None, self.metadata.model_name, "local_python:faster_whisper")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._model is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="transcribe", supported=True, description="Audio transcription"),
            ProviderCapability(name="transcribe_stream", supported=False, description="Streaming transcription"),
            ProviderCapability(name="diarize", supported=True, description="Speaker diarization"),
        ]
    
    async def transcribe(self, audio_path: str, **kwargs) -> GenerationResult:
        """Transcribe audio file to text with timestamps."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            audio_file = Path(audio_path)
            if not audio_file.exists():
                return GenerationResult(success=False, error=f"Audio file not found: {audio_path}")
            
            # Run transcription in thread pool
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self._model.transcribe(
                    str(audio_file),
                    language=kwargs.get("language"),
                    word_timestamps=kwargs.get("word_timestamps", True),
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
            )
            
            # Process segments
            segment_list = []
            full_text = []
            
            for i, segment in enumerate(segments):
                seg_data = {
                    "id": f"seg_{i+1:03d}",
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "speaker": None,  # Would need pyannote for diarization
                    "language": info.language,
                    "confidence": getattr(segment, 'avg_logprob', 0.0),
                }
                
                # Add word timestamps if available
                if hasattr(segment, 'words') and segment.words:
                    seg_data["words"] = [
                        {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                        for w in segment.words
                    ]
                
                segment_list.append(seg_data)
                full_text.append(segment.text.strip())
            
            duration = time.time() - start_time
            
            log_generation(
                None,
                "transcription",
                "local_python:faster_whisper",
                self.metadata.model_name,
                duration
            )
            
            return GenerationResult(
                success=True,
                data={
                    "text": " ".join(full_text),
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "duration": info.duration,
                    "segments": segment_list,
                },
                metadata={
                    "model": self.metadata.model_name,
                    "duration_seconds": duration,
                    "audio_duration": info.duration,
                },
                duration_seconds=duration
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Transcription failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def transcribe_stream(self, audio_stream, **kwargs) -> AsyncIterator[GenerationResult]:
        """Stream transcription (not implemented for faster-whisper)."""
        yield GenerationResult(
            success=False,
            error="Streaming transcription not implemented"
        )
    
    async def cancel(self) -> None:
        """Cancel ongoing transcription."""
        pass


class PyannoteDiarizationProvider:
    """Speaker diarization using pyannote.audio (optional addon)."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._pipeline = None
        self._loaded = False
    
    async def load(self) -> None:
        if self._loaded:
            return
        
        try:
            from pyannote.audio import Pipeline
            import torch
            
            # This requires a Hugging Face token with pyannote access
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.config.get("hf_token"),
            )
            
            if self.config.device == "cuda" and torch.cuda.is_available():
                self._pipeline.to(torch.device("cuda"))
            
            self._loaded = True
            
        except Exception as e:
            self._loaded = False
            # Diarization is optional, don't raise
    
    async def diarize(self, audio_path: str) -> List[Dict[str, Any]]:
        if not self._loaded:
            return []
        
        try:
            import torch
            loop = asyncio.get_event_loop()
            diarization = await loop.run_in_executor(
                None,
                lambda: self._pipeline(audio_path)
            )
            
            speakers = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speakers.append({
                    "speaker": speaker,
                    "start": turn.start,
                    "end": turn.end,
                })
            
            return speakers
            
        except Exception:
            return []
    
    async def unload(self) -> None:
        if self._pipeline:
            del self._pipeline
        self._loaded = False