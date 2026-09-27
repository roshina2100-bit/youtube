"""
Local Python embedding provider using sentence-transformers.
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import EmbeddingProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""
    
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
                ProviderCapability(name="embed", supported=True, description="Text embedding"),
                ProviderCapability(name="embed_batch", supported=True, description="Batch embedding"),
                ProviderCapability(name="similarity", supported=True, description="Cosine similarity"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the sentence transformer model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            self._model = SentenceTransformer(
                model_path,
                device=self.config.device,
                trust_remote_code=self.config.trust_remote_code,
            )
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._last_used = time.time()
            
            log_model_load(
                None,
                self.metadata.model_name,
                "local_python:sentence_transformers",
                self.config.device
            )
            
        except ImportError:
            self._loaded = False
            raise RuntimeError("sentence-transformers not installed. Install with: pip install sentence-transformers")
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load embedding model: {str(e)}") from e
    
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
            
            log_model_unload(None, self.metadata.model_name, "local_python:sentence_transformers")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._model is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="embed", supported=True, description="Text embedding"),
            ProviderCapability(name="embed_batch", supported=True, description="Batch embedding"),
            ProviderCapability(name="similarity", supported=True, description="Cosine similarity"),
        ]
    
    async def embed(self, texts: List[str], **kwargs) -> GenerationResult:
        """Generate embeddings for texts."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            # Ensure texts is a list
            if isinstance(texts, str):
                texts = [texts]
            
            # Run embedding in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self._model.encode(
                    texts,
                    batch_size=kwargs.get("batch_size", 32),
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=kwargs.get("normalize", True),
                )
            )
            
            duration = time.time() - start_time
            
            log_generation(
                None,
                "embedding",
                "local_python:sentence_transformers",
                self.metadata.model_name,
                duration
            )
            
            return GenerationResult(
                success=True,
                data={
                    "embeddings": embeddings.tolist(),
                    "dimension": embeddings.shape[1] if len(embeddings.shape) > 1 else embeddings.shape[0],
                },
                metadata={
                    "model": self.metadata.model_name,
                    "num_texts": len(texts),
                    "duration_seconds": duration,
                },
                duration_seconds=duration
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Embedding failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between embeddings."""
        import numpy as np
        
        arr1 = np.array(embedding1)
        arr2 = np.array(embedding2)
        
        dot = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 > 0 and norm2 > 0:
            return float(dot / (norm1 * norm2))
        return 0.0
    
    async def cancel(self) -> None:
        """Cancel ongoing embedding."""
        pass