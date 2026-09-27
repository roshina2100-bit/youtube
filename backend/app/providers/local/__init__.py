"""
Local Python providers package for the Cinematic Video Studio.
"""

from app.providers.local.llm import TransformersLLMProvider
from app.providers.local.transcription import FasterWhisperTranscriptionProvider, PyannoteDiarizationProvider
from app.providers.local.translation import TransformersTranslationProvider
from app.providers.local.language_detection import FastTextLanguageDetectionProvider
from app.providers.local.embedding import SentenceTransformersEmbeddingProvider
from app.providers.local.image import DiffusersImageProvider
from app.providers.local.tts import TransformersTTSProvider
from app.providers.local.music import TransformersMusicProvider, AudioLDMMusicProvider
from app.providers.local.sfx import TransformersSFXProvider

__all__ = [
    "TransformersLLMProvider",
    "FasterWhisperTranscriptionProvider",
    "PyannoteDiarizationProvider",
    "TransformersTranslationProvider",
    "FastTextLanguageDetectionProvider",
    "SentenceTransformersEmbeddingProvider",
    "DiffusersImageProvider",
    "TransformersTTSProvider",
    "TransformersMusicProvider",
    "AudioLDMMusicProvider",
    "TransformersSFXProvider",
]