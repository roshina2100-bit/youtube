"""
Model Manager Service for the Cinematic Video Studio.
Handles local model loading, unloading, resource monitoring, and capability detection.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.providers.registry import ProviderRegistry
from app.models.provider import ProviderType, ModelConfig, ProviderCapability, ProviderMetadata
from app.core.config import get_settings
from app.core.logging import log_model_load, log_model_unload


class ModelManager:
    """Service for local model lifecycle management."""
    
    def __init__(self, provider_registry: ProviderRegistry):
        self.provider_registry = provider_registry
        self._settings = get_settings()
        self._model_states: Dict[str, Dict[str, Any]] = {}  # key -> {status, loaded_at, last_used, memory_mb}
        self._load_locks: Dict[str, asyncio.Lock] = {}
    
    async def initialize(self) -> None:
        """Initialize model manager with configured models."""
        models_config = self._settings.models.get("models", {})
        
        for model_type, config in models_config.items():
            model_config = ModelConfig(**config)
            self._model_states[model_type] = {
                "status": "unloaded",
                "config": model_config,
                "loaded_at": None,
                "last_used": None,
                "memory_mb": None,
                "load_time": 0.0,
            }
    
    def get_model_status(self, model_type: str) -> Dict[str, Any]:
        """Get status of a model."""
        state = self._model_states.get(model_type, {})
        provider = self.provider_registry.get_provider(
            ProviderType(model_type), "local_python", 
            state.get("config", {}).model_path.split("/")[-1] if state.get("config") else ""
        )
        
        return {
            "model_type": model_type,
            "status": state.get("status", "unknown"),
            "loaded": provider.is_available() if provider else False,
            "config": state.get("config", {}).model_dump() if state.get("config") else {},
            "loaded_at": state.get("loaded_at"),
            "last_used": state.get("last_used"),
            "memory_mb": state.get("memory_mb"),
            "load_time": state.get("load_time", 0.0),
        }
    
    def list_all_models(self) -> List[Dict[str, Any]]:
        """List all configured models with their status."""
        return [self.get_model_status(mt) for mt in self._model_states.keys()]
    
    async def load_model(
        self, 
        model_type: str, 
        provider_name: str = "local_python",
        model_name: Optional[str] = None,
    ) -> bool:
        """Load a model into memory."""
        state = self._model_states.get(model_type)
        if not state:
            raise ValueError(f"Unknown model type: {model_type}")
        
        if state["status"] == "loaded":
            return True
        
        # Get or create lock for this model
        lock_key = f"{model_type}:{provider_name}"
        if lock_key not in self._load_locks:
            self._load_locks[lock_key] = asyncio.Lock()
        
        async with self._load_locks[lock_key]:
            # Double-check after acquiring lock
            if state["status"] == "loaded":
                return True
            
            state["status"] = "loading"
            
            try:
                config = state["config"]
                model_path = config.model_path
                if model_name:
                    model_path = str(Path(model_path).parent / model_name)
                
                # Determine provider type
                provider_type = ProviderType(model_type)
                
                # Load via provider registry
                success = await self.provider_registry.load_provider(
                    ProviderType(model_type), "local_python", 
                    Path(config.model_path).name if config.model_path else model_type
                )
                
                if success:
                    state["status"] = "loaded"
                    state["loaded_at"] = time.time()
                    state["last_used"] = time.time()
                    
                    # Estimate memory usage
                    provider = self.provider_registry.get_provider(
                        ProviderType(model_type), "local_python",
                        Path(config.model_path).name if config.model_path else model_type
                    )
                    if provider and provider.metadata.memory_usage_mb:
                        state["memory_mb"] = provider.metadata.memory_usage_mb
                    
                    log_model_load(
                        None, 
                        Path(config.model_path).name if config.model_path else model_type,
                        "local_python",
                        config.device,
                        state.get("memory_mb")
                    )
                    return True
                else:
                    state["status"] = "failed"
                    return False
                    
            except Exception as e:
                state["status"] = "failed"
                return False
    
    async def unload_model(self, model_type: str) -> bool:
        """Unload a model from memory."""
        state = self._model_states.get(model_type)
        if not state or state["status"] != "loaded":
            return True
        
        try:
            success = await self.provider_registry.unload_provider(
                ProviderType(model_type), "local_python",
                Path(state["config"].model_path).name if state["config"].model_path else model_type
            )
            
            if success:
                state["status"] = "unloaded"
                state["loaded_at"] = None
                state["memory_mb"] = None
                
                log_model_unload(
                    None,
                    Path(state["config"].model_path).name if state["config"].model_path else model_type,
                    "local_python"
                )
                return True
            return False
            
        except Exception:
            return False
    
    async def unload_idle_models(self, idle_timeout: int = 300) -> int:
        """Unload models that have been idle for too long."""
        current_time = time.time()
        unloaded_count = 0
        
        for model_type, state in self._model_states.items():
            if state["status"] == "loaded" and state["last_used"]:
                if current_time - state["last_used"] > idle_timeout:
                    if await self.unload_model(model_type):
                        unloaded_count += 1
        
        return unloaded_count
    
    def mark_model_used(self, model_type: str) -> None:
        """Mark a model as recently used."""
        if model_type in self._model_states:
            self._model_states[model_type]["last_used"] = time.time()
    
    async def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage for all models."""
        total_memory = 0
        loaded_models = []
        
        for model_type, state in self._model_states.items():
            if state["status"] == "loaded":
                mem = state.get("memory_mb", 0)
                total_memory += mem
                loaded_models.append({
                    "model_type": model_type,
                    "memory_mb": mem,
                })
        
        return {
            "total_memory_mb": total_memory,
            "loaded_models": loaded_models,
            "model_count": len(loaded_models),
        }
    
    async def check_model_resources(self, model_type: str) -> Dict[str, Any]:
        """Check if system has enough resources for a model."""
        state = self._model_states.get(model_type)
        if not state:
            return {"available": False, "reason": "Unknown model type"}
        
        config = state.get("config")
        if not config:
            return {"available": False, "reason": "No configuration"}
        
        # Estimate required memory
        estimated_memory = self._estimate_model_memory(config)
        
        # Get current usage
        usage = await self.get_resource_usage()
        current_memory = usage["total_memory_mb"]
        
        # Get system memory (simplified)
        import psutil
        system_memory = psutil.virtual_memory().total / (1024 * 1024)  # MB
        available_memory = system_memory - current_memory
        
        # Check GPU memory if using CUDA
        gpu_available = True
        gpu_memory = 0
        if config.device == "cuda":
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
                    gpu_allocated = torch.cuda.memory_allocated() / (1024 * 1024)
                    gpu_available_memory = gpu_memory - gpu_allocated
                    gpu_available = gpu_available_memory >= estimated_memory
                else:
                    gpu_available = False
            except ImportError:
                gpu_available = False
        
        return {
            "available": available_memory >= estimated_memory and gpu_available,
            "estimated_memory_mb": estimated_memory,
            "available_system_memory_mb": available_memory,
            "available_gpu_memory_mb": gpu_memory if config.device == "cuda" else None,
            "current_usage_mb": current_memory,
            "device": config.device,
        }
    
    def _estimate_model_memory(self, config: ModelConfig) -> int:
        """Estimate model memory requirements in MB."""
        # Rough estimates based on model type and quantization
        base_estimates = {
            "llm": 6000,  # 8B model 4-bit
            "transcription": 2000,
            "translation": 3000,
            "language_detection": 200,
            "embedding": 1000,
            "image": 8000,  # SDXL
            "video": 7000,  # SVD
            "tts": 3000,
            "music": 5000,
            "sfx": 4000,
        }
        
        base = base_estimates.get(config.model_type, 2000)
        
        # Adjust for quantization
        if config.load_in_4bit:
            base = int(base * 0.5)
        elif config.load_in_8bit:
            base = int(base * 0.75)
        
        return base
    
    async def preload_models(self, model_types: List[str]) -> Dict[str, bool]:
        """Preload multiple models."""
        results = {}
        for model_type in model_types:
            results[model_type] = await self.load_model(model_type)
        return results
    
    def get_model_config(self, model_type: str) -> Optional[ModelConfig]:
        """Get model configuration."""
        state = self._model_states.get(model_type)
        return state.get("config") if state else None
    
    def update_model_config(self, model_type: str, config: ModelConfig) -> bool:
        """Update model configuration."""
        if model_type not in self._model_states:
            return False
        
        self._model_states[model_type]["config"] = config
        return True