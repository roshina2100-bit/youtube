"""
Mock providers for testing the Cinematic Video Studio.
Deterministic implementations that work without models, GPU, or internet.
"""

import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ProviderType
from app.providers.interfaces import (
    LLMProvider, TranslationProvider, TranscriptionProvider,
    LanguageDetectionProvider, EmbeddingProvider, ImageGenerationProvider,
    VideoGenerationProvider, TTSProvider, MusicGenerationProvider,
    SoundEffectProvider, GenerationResult
)


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self):
        self._loaded = False
        self._call_log = []
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-llm",
            version="1.0.0",
            capabilities=["generate_text", "structured_output", "chat"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.1)  # Simulate load time
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate_text", supported=True, description="Text generation"),
            ProviderCapability(name="structured_output", supported=True, description="JSON output"),
            ProviderCapability(name="chat", supported=True, description="Multi-turn chat"),
        ]
    
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        self._call_log.append({"prompt": prompt, "kwargs": kwargs})
        await asyncio.sleep(0.05)  # Simulate generation time
        
        # Return deterministic responses based on prompt content
        prompt_lower = prompt.lower()
        
        if "character" in prompt_lower and "json" in prompt_lower:
            return GenerationResult(
                success=True,
                data=json.dumps({
                    "name": "Test Character",
                    "role": "protagonist",
                    "appearance": "Test appearance description",
                    "personality": "Test personality traits",
                    "aliases": ["Alias1", "Alias2"]
                }),
                metadata={"tokens": 100}
            )
        elif "scene" in prompt_lower and "json" in prompt_lower:
            return GenerationResult(
                success=True,
                data=json.dumps({
                    "scene_id": "scene_001",
                    "title": "Test Scene",
                    "description": "A test scene description",
                    "duration": 10.0,
                    "characters": ["char_001"],
                    "location": "Test Location"
                }),
                metadata={"tokens": 150}
            )
        elif "story" in prompt_lower and "json" in prompt_lower:
            return GenerationResult(
                success=True,
                data=json.dumps({
                    "title": "Test Story",
                    "summary": "A test story summary",
                    "acts": [{"act_id": "act_1", "title": "Act 1", "scenes": ["scene_001"]}],
                    "characters": [{"character_id": "char_001", "name": "Test Character"}],
                    "themes": ["test_theme"]
                }),
                metadata={"tokens": 200}
            )
        elif "translate" in prompt_lower:
            return GenerationResult(
                success=True,
                data="Translated text in target language",
                metadata={"tokens": 50}
            )
        elif "prompt" in prompt_lower:
            return GenerationResult(
                success=True,
                data="Cinematic prompt: A detailed cinematic description with lighting, camera, composition details...",
                metadata={"tokens": 200}
            )
        else:
            return GenerationResult(
                success=True,
                data=f"Mock response for: {prompt[:100]}",
                metadata={"tokens": 50}
            )
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        result = await self.generate(prompt, **kwargs)
        if result.success and result.data:
            # Simulate streaming by yielding chunks
            words = str(result.data).split()
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.01)
    
    async def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        return await self.generate(prompt + " Return valid JSON.", **kwargs)
    
    async def cancel(self) -> None:
        pass


class MockTranslationProvider(TranslationProvider):
    """Mock translation provider for testing."""
    
    def __init__(self):
        self._loaded = False
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-translator",
            version="1.0.0",
            capabilities=["translate", "translate_with_context", "translate_batch"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.1)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="translate", supported=True, description="Simple translation"),
            ProviderCapability(name="translate_with_context", supported=True, description="Context-aware translation"),
            ProviderCapability(name="translate_batch", supported=True, description="Batch translation"),
        ]
    
    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> GenerationResult:
        await asyncio.sleep(0.02)
        return GenerationResult(
            success=True,
            data=f"[{target_lang}] {text}",
            metadata={"source_lang": source_lang, "target_lang": target_lang}
        )
    
    async def translate_with_context(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        context: Dict[str, Any],
        **kwargs
    ) -> GenerationResult:
        await asyncio.sleep(0.03)
        return GenerationResult(
            success=True,
            data=f"[{target_lang}] {text} (context-aware)",
            metadata={"source_lang": source_lang, "target_lang": target_lang, "context_used": True}
        )
    
    async def translate_batch(
        self, 
        texts: List[str], 
        source_lang: str, 
        target_lang: str, 
        context: Dict[str, Any],
        **kwargs
    ) -> List[GenerationResult]:
        await asyncio.sleep(0.05)
        return [
            GenerationResult(
                success=True,
                data=f"[{target_lang}] {text}",
                metadata={"source_lang": source_lang, "target_lang": target_lang}
            )
            for text in texts
        ]
    
    async def cancel(self) -> None:
        pass


class MockTranscriptionProvider(TranscriptionProvider):
    """Mock transcription provider for testing."""
    
    def __init__(self):
        self._loaded = False
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-whisper",
            version="1.0.0",
            capabilities=["transcribe", "transcribe_stream", "diarize"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.1)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="transcribe", supported=True, description="Audio transcription"),
            ProviderCapability(name="transcribe_stream", supported=True, description="Streaming transcription"),
            ProviderCapability(name="diarize", supported=True, description="Speaker diarization"),
        ]
    
    async def transcribe(self, audio_path: str, **kwargs) -> GenerationResult:
        await asyncio.sleep(0.1)
        return GenerationResult(
            success=True,
            data={
                "text": "This is a mock transcription of the audio file.",
                "language": kwargs.get("language", "en"),
                "segments": [
                    {"id": "seg_001", "start": 0.0, "end": 5.0, "text": "This is a mock transcription", "speaker": "speaker_1"},
                    {"id": "seg_002", "start": 5.0, "end": 10.0, "text": "of the audio file.", "speaker": "speaker_1"},
                ],
                "speakers": [{"id": "speaker_1", "name": "Speaker 1"}]
            },
            metadata={"duration": 10.0}
        )
    
    async def transcribe_stream(self, audio_stream, **kwargs) -> AsyncIterator[GenerationResult]:
        yield GenerationResult(
            success=True,
            data={"text": "Streaming...", "partial": True}
        )
        await asyncio.sleep(0.1)
        yield GenerationResult(
            success=True,
            data={"text": "This is a mock streaming transcription.", "partial": False}
        )
    
    async def cancel(self) -> None:
        pass


class MockLanguageDetectionProvider(LanguageDetectionProvider):
    """Mock language detection provider for testing."""
    
    def __init__(self):
        self._loaded = False
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-langdetect",
            version="1.0.0",
            capabilities=["detect_text", "detect_audio", "detect_batch"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.05)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="detect_text", supported=True, description="Text language detection"),
            ProviderCapability(name="detect_audio", supported=True, description="Audio language detection"),
            ProviderCapability(name="detect_batch", supported=True, description="Batch detection"),
        ]
    
    async def detect_text(self, text: str, **kwargs) -> GenerationResult:
        await asyncio.sleep(0.01)
        # Simple heuristic: if contains Devanagari, it's Hindi; Telugu script -> Telugu, etc.
        if any('\u0900' <= c <= '\u097F' for c in text):
            lang, conf = "hi", 0.95
        elif any('\u0C00' <= c <= '\u0C7F' for c in text):
            lang, conf = "te", 0.95
        elif any('\u0B80' <= c <= '\u0BFF' for c in text):
            lang, conf = "ta", 0.95
        else:
            lang, conf = "en", 0.9
        
        return GenerationResult(
            success=True,
            data={"language": lang, "confidence": conf, "alternatives": []},
            metadata={}
        )
    
    async def detect_audio(self, audio_path: str, **kwargs) -> GenerationResult:
        await asyncio.sleep(0.05)
        return GenerationResult(
            success=True,
            data={"language": "en", "confidence": 0.9, "alternatives": []},
            metadata={}
        )
    
    async def cancel(self) -> None:
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""
    
    def __init__(self):
        self._loaded = False
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-embedding",
            version="1.0.0",
            capabilities=["embed", "embed_batch", "similarity"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.05)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="embed", supported=True, description="Text embedding"),
            ProviderCapability(name="embed_batch", supported=True, description="Batch embedding"),
            ProviderCapability(name="similarity", supported=True, description="Cosine similarity"),
        ]
    
    async def embed(self, texts: List[str], **kwargs) -> GenerationResult:
        await asyncio.sleep(0.02)
        # Return deterministic fake embeddings
        embeddings = []
        for i, text in enumerate(texts):
            # Simple hash-based embedding
            embedding = [(hash(text + str(j)) % 1000) / 1000.0 for j in range(384)]
            embeddings.append(embedding)
        
        return GenerationResult(
            success=True,
            data={"embeddings": embeddings, "dimension": 384},
            metadata={"model": "mock-embedding"}
        )
    
    async def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        # Simple cosine similarity
        dot = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5
        return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
    
    async def cancel(self) -> None:
        pass


class MockImageGenerationProvider(ImageGenerationProvider):
    """Mock image generation provider for testing."""
    
    def __init__(self):
        self._loaded = False
        self._generated_images = 0
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-sdxl",
            version="1.0.0",
            capabilities=["generate", "generate_with_reference", "inpaint", "outpaint"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.2)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate", supported=True, description="Text-to-image"),
            ProviderCapability(name="generate_with_reference", supported=True, description="Image-to-image"),
            ProviderCapability(name="inpaint", supported=True, description="Inpainting"),
            ProviderCapability(name="outpaint", supported=True, description="Outpainting"),
        ]
    
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        self._generated_images += 1
        await asyncio.sleep(0.1)
        
        # Create a simple colored image as bytes (1x1 pixel PNG)
        # In real implementation, this would be actual image bytes
        width = kwargs.get("width", 1024)
        height = kwargs.get("height", 1024)
        
        return GenerationResult(
            success=True,
            data={
                "image_path": f"mock_image_{self._generated_images:03d}.png",
                "width": width,
                "height": height,
                "prompt": prompt,
                "seed": kwargs.get("seed", 12345),
                "format": "png"
            },
            metadata={"generation_time": 0.1}
        )
    
    async def generate_with_reference(
        self, 
        prompt: str, 
        reference_image: str, 
        **kwargs
    ) -> GenerationResult:
        return await self.generate(prompt + " (with reference)", **kwargs)
    
    async def inpaint(self, image: str, mask: str, prompt: str, **kwargs) -> GenerationResult:
        return await self.generate(prompt + " (inpainted)", **kwargs)
    
    async def outpaint(self, image: str, prompt: str, **kwargs) -> GenerationResult:
        return await self.generate(prompt + " (outpainted)", **kwargs)
    
    async def cancel(self) -> None:
        pass


class MockVideoGenerationProvider(VideoGenerationProvider):
    """Mock video generation provider for testing."""
    
    def __init__(self):
        self._loaded = False
        self._generated_videos = 0
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-svd",
            version="1.0.0",
            capabilities=["generate", "generate_text_to_video", "interpolate"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.2)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate", supported=True, description="Image-to-video"),
            ProviderCapability(name="generate_text_to_video", supported=False, description="Text-to-video (not supported)"),
            ProviderCapability(name="interpolate", supported=True, description="Frame interpolation"),
        ]
    
    async def generate(self, image_path: str, prompt: str, **kwargs) -> GenerationResult:
        self._generated_videos += 1
        await asyncio.sleep(0.2)
        
        num_frames = kwargs.get("num_frames", 25)
        fps = kwargs.get("fps", 7)
        
        return GenerationResult(
            success=True,
            data={
                "video_path": f"mock_video_{self._generated_videos:03d}.mp4",
                "num_frames": num_frames,
                "fps": fps,
                "duration_seconds": num_frames / fps,
                "prompt": prompt,
                "source_image": image_path
            },
            metadata={"generation_time": 0.2}
        )
    
    async def generate_text_to_video(self, prompt: str, **kwargs) -> GenerationResult:
        return GenerationResult(
            success=False,
            error="Text-to-video not supported in mock provider"
        )
    
    async def interpolate(self, frames: List[str], **kwargs) -> GenerationResult:
        await asyncio.sleep(0.1)
        return GenerationResult(
            success=True,
            data={"interpolated_frames": len(frames) * 2}
        )
    
    async def cancel(self) -> None:
        pass


class MockTTSProvider(TTSProvider):
    """Mock TTS provider for testing."""
    
    def __init__(self):
        self._loaded = False
        self._generated_audio = 0
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-xtts",
            version="1.0.0",
            capabilities=["synthesize", "synthesize_stream", "clone_voice", "list_voices"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.1)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="synthesize", supported=True, description="Text-to-speech"),
            ProviderCapability(name="synthesize_stream", supported=True, description="Streaming TTS"),
            ProviderCapability(name="clone_voice", supported=True, description="Voice cloning"),
            ProviderCapability(name="list_voices", supported=True, description="List voices"),
        ]
    
    async def synthesize(self, text: str, voice_id: str, **kwargs) -> GenerationResult:
        self._generated_audio += 1
        await asyncio.sleep(0.05)
        
        return GenerationResult(
            success=True,
            data={
                "audio_path": f"mock_tts_{self._generated_audio:03d}.wav",
                "duration_seconds": len(text) * 0.1,
                "voice_id": voice_id,
                "text": text,
                "sample_rate": 22050
            },
            metadata={"generation_time": 0.05}
        )
    
    async def synthesize_stream(self, text: str, voice_id: str, **kwargs) -> AsyncIterator[bytes]:
        # Yield fake audio chunks
        for i in range(10):
            yield b"\x00" * 1024  # Silent audio chunk
            await asyncio.sleep(0.01)
    
    async def clone_voice(self, reference_audio: str, **kwargs) -> GenerationResult:
        await asyncio.sleep(0.1)
        return GenerationResult(
            success=True,
            data={"voice_id": "cloned_voice_001", "reference": reference_audio}
        )
    
    async def list_voices(self) -> GenerationResult:
        return GenerationResult(
            success=True,
            data={
                "voices": [
                    {"id": "voice_1", "name": "Default Male", "language": "en"},
                    {"id": "voice_2", "name": "Default Female", "language": "en"},
                    {"id": "voice_3", "name": "Narrator", "language": "en"},
                ]
            }
        )
    
    async def cancel(self) -> None:
        pass


class MockMusicGenerationProvider(MusicGenerationProvider):
    """Mock music generation provider for testing."""
    
    def __init__(self):
        self._loaded = False
        self._generated_music = 0
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-musicgen",
            version="1.0.0",
            capabilities=["generate", "generate_with_melody", "continue"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.1)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate", supported=True, description="Text-to-music"),
            ProviderCapability(name="generate_with_melody", supported=True, description="Melody-conditioned"),
            ProviderCapability(name="continue", supported=True, description="Continue music"),
        ]
    
    async def generate(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        self._generated_music += 1
        await asyncio.sleep(0.1)
        
        return GenerationResult(
            success=True,
            data={
                "audio_path": f"mock_music_{self._generated_music:03d}.wav",
                "duration_seconds": duration,
                "prompt": prompt,
                "sample_rate": 32000
            },
            metadata={"generation_time": 0.1}
        )
    
    async def generate_with_melody(self, prompt: str, melody_path: str, **kwargs) -> GenerationResult:
        return await self.generate(prompt + " (with melody)", kwargs.get("duration", 30))
    
    async def continue_music(self, audio_path: str, duration: float, **kwargs) -> GenerationResult:
        return await self.generate("Continuation of " + audio_path, duration)
    
    async def cancel(self) -> None:
        pass


class MockSFXProvider(SoundEffectProvider):
    """Mock sound effect provider for testing."""
    
    def __init__(self):
        self._loaded = False
        self._generated_sfx = 0
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-audioldm",
            version="1.0.0",
            capabilities=["generate", "generate_variations"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self) -> None:
        await asyncio.sleep(0.1)
        self._loaded = True
    
    async def unload(self) -> None:
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate", supported=True, description="Text-to-SFX"),
            ProviderCapability(name="generate_variations", supported=True, description="Multiple variations"),
        ]
    
    async def generate(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        self._generated_sfx += 1
        await asyncio.sleep(0.05)
        
        return GenerationResult(
            success=True,
            data={
                "audio_path": f"mock_sfx_{self._generated_sfx:03d}.wav",
                "duration_seconds": duration,
                "prompt": prompt,
                "sample_rate": 16000
            },
            metadata={"generation_time": 0.05}
        )
    
    async def generate_variations(self, prompt: str, duration: float, count: int, **kwargs) -> List[GenerationResult]:
        await asyncio.sleep(0.1)
        return [
            GenerationResult(
                success=True,
                data={
                    "audio_path": f"mock_sfx_{self._generated_sfx + i + 1:03d}.wav",
                    "duration_seconds": duration,
                    "prompt": prompt,
                    "variation": i + 1
                }
            )
            for i in range(count)
        ]
    
    async def cancel(self) -> None:
        pass