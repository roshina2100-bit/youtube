"""
Provider interfaces for the Cinematic Video Studio.
Abstract base classes that all providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel
from app.models.provider import ProviderMetadata, ProviderCapability, ProviderType


class GenerationResult(BaseModel):
    """Base result for generation operations."""
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    duration_seconds: float = 0.0


class LLMProvider(ABC):
    """Interface for LLM text generation providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Get provider metadata."""
        pass
    
    @abstractmethod
    async def load(self) -> None:
        """Load the model into memory."""
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        """Unload the model from memory."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available for use."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        """Get list of supported capabilities."""
        pass
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream text generation."""
        pass
    
    @abstractmethod
    async def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        """Generate structured output (JSON) conforming to schema."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        """Cancel any ongoing generation."""
        pass


class TranslationProvider(ABC):
    """Interface for translation providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> GenerationResult:
        """Translate text from source to target language."""
        pass
    
    @abstractmethod
    async def translate_with_context(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        context: Dict[str, Any],
        **kwargs
    ) -> GenerationResult:
        """Translate with full context (scene, characters, etc.)."""
        pass
    
    @abstractmethod
    async def translate_batch(
        self, 
        texts: List[str], 
        source_lang: str, 
        target_lang: str, 
        context: Dict[str, Any],
        **kwargs
    ) -> List[GenerationResult]:
        """Translate multiple texts with shared context."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


class TranscriptionProvider(ABC):
    """Interface for speech-to-text providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def transcribe(self, audio_path: str, **kwargs) -> GenerationResult:
        """Transcribe audio file to text with timestamps."""
        pass
    
    @abstractmethod
    async def transcribe_stream(self, audio_stream, **kwargs) -> AsyncIterator[GenerationResult]:
        """Stream transcription from audio stream."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


class LanguageDetectionProvider(ABC):
    """Interface for language detection providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def detect_text(self, text: str, **kwargs) -> GenerationResult:
        """Detect language from text."""
        pass
    
    @abstractmethod
    async def detect_audio(self, audio_path: str, **kwargs) -> GenerationResult:
        """Detect language from audio."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


class EmbeddingProvider(ABC):
    """Interface for embedding providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def embed(self, texts: List[str], **kwargs) -> GenerationResult:
        """Generate embeddings for texts."""
        pass
    
    @abstractmethod
    async def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between embeddings."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


class ImageGenerationProvider(ABC):
    """Interface for image generation providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        """Generate image from text prompt."""
        pass
    
    @abstractmethod
    async def generate_with_reference(
        self, 
        prompt: str, 
        reference_image: str, 
        **kwargs
    ) -> GenerationResult:
        """Generate image with reference (IP-Adapter, ControlNet, etc.)."""
        pass
    
    @abstractmethod
    async def inpaint(self, image: str, mask: str, prompt: str, **kwargs) -> GenerationResult:
        """Inpaint image."""
        pass
    
    @abstractmethod
    async def outpaint(self, image: str, prompt: str, **kwargs) -> GenerationResult:
        """Outpaint image."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


class VideoGenerationProvider(ABC):
    """Interface for video generation providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def generate(self, image_path: str, prompt: str, **kwargs) -> GenerationResult:
        """Generate video from image (image-to-video)."""
        pass
    
    @abstractmethod
    async def generate_text_to_video(self, prompt: str, **kwargs) -> GenerationResult:
        """Generate video from text (text-to-video)."""
        pass
    
    @abstractmethod
    async def interpolate(self, frames: List[str], **kwargs) -> GenerationResult:
        """Interpolate between frames."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


class TTSProvider(ABC):
    """Interface for text-to-speech providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, **kwargs) -> GenerationResult:
        """Synthesize speech from text."""
        pass
    
    @abstractmethod
    async def synthesize_stream(self, text: str, voice_id: str, **kwargs) -> AsyncIterator[bytes]:
        """Stream speech synthesis."""
        pass
    
    @abstractmethod
    async def clone_voice(self, reference_audio: str, **kwargs) -> GenerationResult:
        """Clone voice from reference audio."""
        pass
    
    @abstractmethod
    async def list_voices(self) -> GenerationResult:
        """List available voices."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


class MusicGenerationProvider(ABC):
    """Interface for music generation providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def generate(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        """Generate music from text prompt."""
        pass
    
    @abstractmethod
    async def generate_with_melody(self, prompt: str, melody_path: str, **kwargs) -> GenerationResult:
        """Generate music conditioned on melody."""
        pass
    
    @abstractmethod
    async def continue_music(self, audio_path: str, duration: float, **kwargs) -> GenerationResult:
        """Continue existing music."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


class SoundEffectProvider(ABC):
    """Interface for sound effect generation providers."""
    
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        pass
    
    @abstractmethod
    async def load(self) -> None:
        pass
    
    @abstractmethod
    async def unload(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[ProviderCapability]:
        pass
    
    @abstractmethod
    async def generate(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        """Generate sound effect from text prompt."""
        pass
    
    @abstractmethod
    async def generate_variations(self, prompt: str, duration: float, count: int, **kwargs) -> List[GenerationResult]:
        """Generate multiple variations."""
        pass
    
    @abstractmethod
    async def cancel(self) -> None:
        pass


# Provider type mapping for registry
PROVIDER_INTERFACES = {
    ProviderType.LLM: LLMProvider,
    ProviderType.TRANSLATION: TranslationProvider,
    ProviderType.TRANSCRIPTION: TranscriptionProvider,
    ProviderType.LANGUAGE_DETECTION: LanguageDetectionProvider,
    ProviderType.EMBEDDING: EmbeddingProvider,
    ProviderType.IMAGE_GENERATION: ImageGenerationProvider,
    ProviderType.VIDEO_GENERATION: VideoGenerationProvider,
    ProviderType.TTS: TTSProvider,
    ProviderType.MUSIC_GENERATION: MusicGenerationProvider,
    ProviderType.SFX_GENERATION: SoundEffectProvider,
}