"""
NotebookLM / External API provider adapter for the Cinematic Video Studio.
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from app.models.provider import ProviderMetadata, ProviderCapability, ProviderType
from app.providers.interfaces import (
    LLMProvider, TranslationProvider, TranscriptionProvider,
    LanguageDetectionProvider, EmbeddingProvider, ImageGenerationProvider,
    VideoGenerationProvider, TTSProvider, MusicGenerationProvider,
    SoundEffectProvider, GenerationResult
)
from app.core.config import get_settings, NotebookLMConfig
from app.core.logging import log_generation


class NotebookLMProvider(LLMProvider, TranslationProvider):
    """Adapter for NotebookLM or compatible API endpoints.
    
    Note: NotebookLM does not currently have a public API.
    This is a placeholder for future API integrations or custom endpoints.
    """
    
    def __init__(self, config: NotebookLMConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._loaded = False
        self._load_time = 0.0
        self._last_used = None
        self._capabilities = self._detect_capabilities()
    
    def _detect_capabilities(self) -> List[ProviderCapability]:
        """Detect supported capabilities based on configuration."""
        caps = [
            ProviderCapability(name="generate_text", supported=True, description="Text generation"),
            ProviderCapability(name="structured_output", supported=True, description="JSON output"),
            ProviderCapability(name="translate", supported=True, description="Translation"),
            ProviderCapability(name="translate_with_context", supported=True, description="Context-aware translation"),
        ]
        
        # These are typically NOT supported by NotebookLM
        unsupported = [
            "transcribe", "detect_text", "detect_audio", "embed",
            "generate_image", "generate_video", "synthesize_speech",
            "generate_music", "generate_sfx"
        ]
        
        for cap in unsupported:
            caps.append(ProviderCapability(
                name=cap, 
                supported=False, 
                description=f"{cap} not supported by NotebookLM"
            ))
        
        return caps
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="notebooklm",
            model_name=self.config.model or "unknown",
            version="1.0.0",
            capabilities=self._capabilities,
            loaded=self._loaded,
            device="cloud",
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Initialize HTTP client and test connection."""
        if self._loaded:
            return
        
        if not self.config.enabled:
            raise RuntimeError("NotebookLM provider is not enabled in configuration")
        
        if not self.config.api_key:
            raise RuntimeError("NotebookLM API key not configured")
        
        if not self.config.endpoint:
            raise RuntimeError("NotebookLM endpoint not configured")
        
        start_time = time.time()
        
        try:
            self._client = httpx.AsyncClient(
                base_url=self.config.endpoint.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout_seconds,
            )
            
            # Test connection
            await self.test_connection()
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._last_used = time.time()
            
        except Exception as e:
            self._loaded = False
            if self._client:
                await self._client.aclose()
                self._client = None
            raise RuntimeError(f"Failed to initialize NotebookLM provider: {str(e)}") from e
    
    async def unload(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._loaded = False
    
    def is_available(self) -> bool:
        return self._loaded and self._client is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return self._capabilities
    
    async def test_connection(self) -> bool:
        """Test connection to NotebookLM API."""
        if not self._client:
            return False
        
        try:
            # Try a simple health check or list models endpoint
            response = await self._client.get("/v1/models")
            return response.status_code == 200
        except Exception:
            return False
    
    # LLMProvider methods
    
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        """Generate text from prompt."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Provider not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "stop": kwargs.get("stop_sequences"),
            }
            
            response = await self._client.post(
                "/v1/completions",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            generated_text = data["choices"][0]["text"]
            
            duration = time.time() - start_time
            
            log_generation(
                None,
                "text_generation",
                "notebooklm",
                self.config.model,
                duration
            )
            
            return GenerationResult(
                success=True,
                data=generated_text,
                metadata={
                    "model": self.config.model,
                    "usage": data.get("usage", {}),
                    "duration_seconds": duration,
                },
                duration_seconds=duration
            )
            
        except httpx.HTTPStatusError as e:
            return GenerationResult(
                success=False,
                error=f"API error: {e.response.status_code} - {e.response.text}",
                duration_seconds=time.time() - start_time
            )
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream text generation."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            yield "Provider not loaded"
            return
        
        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "stream": True,
            }
            
            async with self._client.stream("POST", "/v1/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            if data["choices"][0]["text"]:
                                yield data["choices"][0]["text"]
                        except Exception:
                            pass
                            
        except Exception as e:
            yield f"Error: {str(e)}"
    
    async def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        """Generate structured JSON output."""
        structured_prompt = f"{prompt}\n\nReturn only valid JSON matching this schema: {json.dumps(schema)}"
        return await self.generate(structured_prompt, **kwargs)
    
    async def cancel(self) -> None:
        """Cancel ongoing generation."""
        pass
    
    # TranslationProvider methods
    
    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> GenerationResult:
        """Translate text from source to target language."""
        prompt = f"Translate the following {source_lang} text to {target_lang}:\n\n{text}\n\nTranslation:"
        return await self.generate(prompt, **kwargs)
    
    async def translate_with_context(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        context: Dict[str, Any],
        **kwargs
    ) -> GenerationResult:
        """Translate with full context (scene, characters, etc.)."""
        context_parts = []
        if context.get("scene_description"):
            context_parts.append(f"Scene: {context['scene_description']}")
        if context.get("characters"):
            context_parts.append(f"Characters: {', '.join(context['characters'])}")
        if context.get("previous_scene"):
            context_parts.append(f"Previous scene: {context['previous_scene']}")
        if context.get("next_scene"):
            context_parts.append(f"Next scene: {context['next_scene']}")
        if context.get("emotion"):
            context_parts.append(f"Emotional tone: {context['emotion']}")
        if context.get("cultural_context"):
            context_parts.append(f"Cultural context: {context['cultural_context']}")
        
        context_str = "\n".join(context_parts) if context_parts else "No additional context."
        
        prompt = f"""Translate the following {source_lang} text to {target_lang}.

Context:
{context_str}

Text to translate:
{text}

Translation:"""
        
        return await self.generate(prompt, **kwargs)
    
    async def translate_batch(
        self, 
        texts: List[str], 
        source_lang: str, 
        target_lang: str, 
        context: Dict[str, Any],
        **kwargs
    ) -> List[GenerationResult]:
        """Translate multiple texts with shared context."""
        # For API providers, batch translate by sending all at once
        combined_text = "\n\n---\n\n".join(texts)
        result = await self.translate_with_context(combined_text, source_lang, target_lang, context, **kwargs)
        
        if result.success:
            # Split results back
            translations = result.data.split("\n\n---\n\n")
            return [
                GenerationResult(
                    success=True,
                    data=t.strip(),
                    metadata=result.metadata,
                    duration_seconds=result.duration_seconds / len(texts)
                )
                for t in translations
            ]
        else:
            return [result for _ in texts]
    
    # Unsupported methods (raise NotImplementedError)
    
    async def transcribe(self, audio_path: str, **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="Transcription not supported by NotebookLM")
    
    async def transcribe_stream(self, audio_stream, **kwargs) -> AsyncIterator[GenerationResult]:
        yield GenerationResult(success=False, error="Transcription not supported by NotebookLM")
    
    async def detect_text(self, text: str, **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="Language detection not supported by NotebookLM")
    
    async def detect_audio(self, audio_path: str, **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="Language detection not supported by NotebookLM")
    
    async def embed(self, texts: List[str], **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="Embeddings not supported by NotebookLM")
    
    async def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        return 0.0
    
    async def generate_image(self, prompt: str, **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="Image generation not supported by NotebookLM")
    
    async def generate_video(self, image_path: str, prompt: str, **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="Video generation not supported by NotebookLM")
    
    async def synthesize(self, text: str, voice_id: str, **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="TTS not supported by NotebookLM")
    
    async def generate_music(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="Music generation not supported by NotebookLM")
    
    async def generate_sfx(self, prompt: str, duration: float, **kwargs) -> GenerationResult:
        return GenerationResult(success=False, error="SFX generation not supported by NotebookLM")


# Import json at module level
import json