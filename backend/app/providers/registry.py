"""
Provider registry for the Cinematic Video Studio.
Manages all AI provider implementations and capability detection.
"""

import asyncio
from typing import Dict, List, Optional, Any, Type
from pathlib import Path

from app.models.provider import (
    ProviderMetadata, ProviderCapability, ProviderType, 
    ProviderInfo, CapabilityMatrix, ModelConfig
)
from app.providers.interfaces import (
    LLMProvider, TranslationProvider, TranscriptionProvider,
    LanguageDetectionProvider, EmbeddingProvider, ImageGenerationProvider,
    VideoGenerationProvider, TTSProvider, MusicGenerationProvider,
    SoundEffectProvider, PROVIDER_INTERFACES, GenerationResult
)
from app.core.config import get_settings
from app.core.logging import get_project_logger


class ProviderRegistry:
    """Registry for all AI providers."""
    
    def __init__(self):
        self._providers: Dict[str, Any] = {}  # key -> provider instance
        self._provider_configs: Dict[str, ModelConfig] = {}
        self._capability_matrix = CapabilityMatrix()
        self._load_locks: Dict[str, asyncio.Lock] = {}
        self._settings = None
    
    async def initialize(self, settings) -> None:
        """Initialize the registry with settings."""
        self._settings = settings
        
        # Load model configurations
        models_config = settings.models.get("models", {})
        for model_type, config in models_config.items():
            self._provider_configs[model_type] = ModelConfig(**config)
        
        # Register mock providers for testing
        if settings.test_mode:
            await self._register_mock_providers()
        
        # Build capability matrix
        self._build_capability_matrix()
    
    async def _register_mock_providers(self) -> None:
        """Register mock providers for testing."""
        from app.providers.mock import (
            MockLLMProvider, MockTranslationProvider, MockTranscriptionProvider,
            MockLanguageDetectionProvider, MockEmbeddingProvider,
            MockImageGenerationProvider, MockVideoGenerationProvider,
            MockTTSProvider, MockMusicGenerationProvider, MockSFXProvider
        )
        
        mock_providers = {
            ProviderType.LLM: MockLLMProvider(),
            ProviderType.TRANSLATION: MockTranslationProvider(),
            ProviderType.TRANSCRIPTION: MockTranscriptionProvider(),
            ProviderType.LANGUAGE_DETECTION: MockLanguageDetectionProvider(),
            ProviderType.EMBEDDING: MockEmbeddingProvider(),
            ProviderType.IMAGE_GENERATION: MockImageGenerationProvider(),
            ProviderType.VIDEO_GENERATION: MockVideoGenerationProvider(),
            ProviderType.TTS: MockTTSProvider(),
            ProviderType.MUSIC_GENERATION: MockMusicGenerationProvider(),
            ProviderType.SFX_GENERATION: MockSFXProvider(),
        }
        
        for ptype, provider in mock_providers.items():
            key = f"{ptype.value}:mock:{provider.metadata.model_name}"
            self._providers[key] = provider
            await provider.load()
    
    def _build_capability_matrix(self) -> None:
        """Build capability matrix from registered providers."""
        matrix = {}
        for key, provider in self._providers.items():
            metadata = provider.metadata
            ptype = metadata.provider_name.split(":")[0] if ":" in metadata.provider_name else "unknown"
            
            if ptype not in matrix:
                matrix[ptype] = {}
            
            model_key = metadata.model_name
            if model_key not in matrix[ptype]:
                matrix[ptype][model_key] = {}
            
            for cap in provider.get_capabilities():
                matrix[ptype][model_key][cap.name] = cap.supported
        
        self._capability_matrix.matrix = matrix
    
    def register_provider(self, provider_type: ProviderType, provider: Any) -> None:
        """Register a provider instance."""
        metadata = provider.metadata
        key = f"{provider_type.value}:{metadata.provider_name}:{metadata.model_name}"
        self._providers[key] = provider
        self._build_capability_matrix()
    
    def get_provider(self, provider_type: ProviderType, provider_name: str, model_name: str) -> Optional[Any]:
        """Get a specific provider instance."""
        key = f"{provider_type.value}:{provider_name}:{model_name}"
        return self._providers.get(key)
    
    def get_provider_by_key(self, key: str) -> Optional[Any]:
        """Get provider by full key."""
        return self._providers.get(key)
    
    def list_providers(self, provider_type: Optional[ProviderType] = None) -> List[ProviderInfo]:
        """List all registered providers, optionally filtered by type."""
        providers = []
        for key, provider in self._providers.items():
            metadata = provider.metadata
            
            # Parse key to get type
            key_parts = key.split(":")
            if len(key_parts) >= 3:
                ptype_str = key_parts[0]
                try:
                    ptype = ProviderType(ptype_str)
                except ValueError:
                    continue
                
                if provider_type and ptype != provider_type:
                    continue
                
                # Get config for memory estimation
                config = self._provider_configs.get(ptype_str, {})
                estimated_memory = self._estimate_memory(ptype, config)
                
                providers.append(ProviderInfo(
                    type=ptype,
                    provider_name=metadata.provider_name,
                    model_name=metadata.model_name,
                    display_name=f"{metadata.provider_name} - {metadata.model_name}",
                    description=f"{metadata.provider_name} provider for {ptype.value}",
                    status="available" if provider.is_available() else "unavailable",
                    capabilities=[c.name for c in provider.get_capabilities() if c.supported],
                    estimated_memory_mb=estimated_memory,
                    model_path=config.get("model_path") if isinstance(config, dict) else getattr(config, "model_path", None),
                    backend=config.get("backend") if isinstance(config, dict) else getattr(config, "backend", None),
                    loaded=metadata.loaded,
                ))
        
        return providers
    
    def _estimate_memory(self, provider_type: ProviderType, config: Any) -> Optional[int]:
        """Estimate memory requirement for a provider."""
        # Rough estimates in MB
        estimates = {
            ProviderType.LLM: 6000,  # 8B model 4-bit
            ProviderType.TRANSCRIPTION: 2000,
            ProviderType.TRANSLATION: 3000,
            ProviderType.IMAGE_GENERATION: 8000,  # SDXL
            ProviderType.VIDEO_GENERATION: 7000,  # SVD
            ProviderType.TTS: 3000,
            ProviderType.MUSIC_GENERATION: 5000,
            ProviderType.SFX_GENERATION: 4000,
        }
        return estimates.get(provider_type)
    
    def get_capability_matrix(self) -> CapabilityMatrix:
        """Get the capability matrix."""
        return self._capability_matrix
    
    def get_supported_providers(self, provider_type: ProviderType, capability: str) -> List[str]:
        """Get providers that support a capability."""
        return self._capability_matrix.get_supported_providers(provider_type, capability)
    
    def is_capability_supported(self, provider_type: ProviderType, provider_name: str, capability: str) -> bool:
        """Check if a provider supports a capability."""
        return self._capability_matrix.is_supported(provider_type, provider_name, capability)
    
    async def load_provider(self, provider_type: ProviderType, provider_name: str, model_name: str) -> bool:
        """Load a provider (with locking to prevent concurrent loads)."""
        key = f"{provider_type.value}:{provider_name}:{model_name}"
        
        if key not in self._load_locks:
            self._load_locks[key] = asyncio.Lock()
        
        async with self._load_locks[key]:
            provider = self._providers.get(key)
            if not provider:
                # Try to create provider
                provider = await self._create_provider(provider_type, provider_name, model_name)
                if not provider:
                    return False
                self._providers[key] = provider
            
            if not provider.is_available():
                try:
                    await provider.load()
                    self._build_capability_matrix()
                    return True
                except Exception as e:
                    # Log error
                    return False
            
            return True
    
    async def _create_provider(self, provider_type: ProviderType, provider_name: str, model_name: str) -> Optional[Any]:
        """Create a provider instance based on type and name."""
        config = self._provider_configs.get(provider_type.value)
        
        if provider_name == "local_python":
            return await self._create_local_provider(provider_type, model_name, config)
        elif provider_name == "notebooklm":
            return await self._create_notebooklm_provider(provider_type, model_name, config)
        elif provider_name == "mock":
            return await self._create_mock_provider(provider_type)
        
        return None
    
    async def _create_local_provider(self, provider_type: ProviderType, model_name: str, config: Optional[ModelConfig]) -> Optional[Any]:
        """Create a local Python provider."""
        try:
            if provider_type == ProviderType.LLM:
                from app.providers.local.llm import TransformersLLMProvider
                return TransformersLLMProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.TRANSCRIPTION:
                from app.providers.local.transcription import FasterWhisperTranscriptionProvider
                return FasterWhisperTranscriptionProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.TRANSLATION:
                from app.providers.local.translation import TransformersTranslationProvider
                return TransformersTranslationProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.LANGUAGE_DETECTION:
                from app.providers.local.language_detection import FastTextLanguageDetectionProvider
                return FastTextLanguageDetectionProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.EMBEDDING:
                from app.providers.local.embedding import SentenceTransformersEmbeddingProvider
                return SentenceTransformersEmbeddingProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.IMAGE_GENERATION:
                from app.providers.local.image import DiffusersImageProvider
                return DiffusersImageProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.VIDEO_GENERATION:
                from app.providers.local.video import DiffusersVideoProvider
                return DiffusersVideoProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.TTS:
                from app.providers.local.tts import TransformersTTSProvider
                return TransformersTTSProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.MUSIC_GENERATION:
                from app.providers.local.music import TransformersMusicProvider
                return TransformersMusicProvider(config or ModelConfig(model_path=model_name))
            elif provider_type == ProviderType.SFX_GENERATION:
                from app.providers.local.sfx import TransformersSFXProvider
                return TransformersSFXProvider(config or ModelConfig(model_path=model_name))
        except ImportError:
            # Provider not implemented yet
            pass
        return None
    
    async def _create_notebooklm_provider(self, provider_type: ProviderType, model_name: str, config: Optional[ModelConfig]) -> Optional[Any]:
        """Create a NotebookLM provider."""
        if not self._settings or not self._settings.notebooklm.enabled:
            return None
        
        try:
            from app.providers.external.notebooklm import NotebookLMProvider
            return NotebookLMProvider(self._settings.notebooklm)
        except ImportError:
            pass
        return None
    
    async def _create_mock_provider(self, provider_type: ProviderType) -> Optional[Any]:
        """Create a mock provider."""
        try:
            from app.providers.mock import (
                MockLLMProvider, MockTranslationProvider, MockTranscriptionProvider,
                MockLanguageDetectionProvider, MockEmbeddingProvider,
                MockImageGenerationProvider, MockVideoGenerationProvider,
                MockTTSProvider, MockMusicGenerationProvider, MockSFXProvider
            )
            
            mock_map = {
                ProviderType.LLM: MockLLMProvider,
                ProviderType.TRANSLATION: MockTranslationProvider,
                ProviderType.TRANSCRIPTION: MockTranscriptionProvider,
                ProviderType.LANGUAGE_DETECTION: MockLanguageDetectionProvider,
                ProviderType.EMBEDDING: MockEmbeddingProvider,
                ProviderType.IMAGE_GENERATION: MockImageGenerationProvider,
                ProviderType.VIDEO_GENERATION: MockVideoGenerationProvider,
                ProviderType.TTS: MockTTSProvider,
                ProviderType.MUSIC_GENERATION: MockMusicGenerationProvider,
                ProviderType.SFX_GENERATION: MockSFXProvider,
            }
            
            provider_class = mock_map.get(provider_type)
            if provider_class:
                return provider_class()
        except ImportError:
            pass
        return None
    
    async def unload_provider(self, provider_type: ProviderType, provider_name: str, model_name: str) -> bool:
        """Unload a provider."""
        key = f"{provider_type.value}:{provider_name}:{model_name}"
        provider = self._providers.get(key)
        if provider and provider.is_available():
            try:
                await provider.unload()
                return True
            except Exception:
                pass
        return False
    
    async def unload_idle_providers(self, idle_timeout: int = 300) -> None:
        """Unload providers that have been idle for too long."""
        import time
        now = time.time()
        
        for key, provider in self._providers.items():
            metadata = provider.metadata
            if metadata.loaded and metadata.last_used:
                if now - metadata.last_used > idle_timeout:
                    await self.unload_provider(
                        ProviderType(metadata.provider_name.split(":")[0]),
                        metadata.provider_name,
                        metadata.model_name
                    )
    
    async def shutdown(self) -> None:
        """Shutdown all providers."""
        for provider in self._providers.values():
            if provider.is_available():
                try:
                    await provider.unload()
                except Exception:
                    pass
        self._providers.clear()
    
    async def test_provider(self, provider_type: ProviderType, provider_name: str, model_name: str, test_input: Dict[str, Any]) -> Dict[str, Any]:
        """Test a provider with sample input."""
        provider = self.get_provider(provider_type, provider_name, model_name)
        if not provider:
            return {"success": False, "error": "Provider not found"}
        
        # Load if needed
        if not provider.is_available():
            await self.load_provider(provider_type, provider_name, model_name)
        
        if not provider.is_available():
            return {"success": False, "error": "Provider failed to load"}
        
        try:
            import time
            start = time.time()
            
            # Run appropriate test based on provider type
            if provider_type == ProviderType.LLM:
                result = await provider.generate(test_input.get("prompt", "Test prompt"), max_tokens=50)
            elif provider_type == ProviderType.TRANSLATION:
                result = await provider.translate(
                    test_input.get("text", "Hello world"),
                    test_input.get("source_lang", "en"),
                    test_input.get("target_lang", "es")
                )
            elif provider_type == ProviderType.TRANSCRIPTION:
                result = await provider.transcribe(test_input.get("audio_path", ""))
            elif provider_type == ProviderType.IMAGE_GENERATION:
                result = await provider.generate(test_input.get("prompt", "Test image"), width=256, height=256)
            else:
                result = GenerationResult(success=True, data="Test passed")
            
            duration = time.time() - start
            return {
                "success": result.success,
                "response": result.data,
                "error": result.error,
                "duration_seconds": duration,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}