"""
Models API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.core.config import get_settings
from app.providers.registry import ProviderRegistry


router = APIRouter()


def get_provider_registry() -> ProviderRegistry:
    from app.main import app
    return app.state.provider_registry


class ModelInfo(BaseModel):
    type: str
    provider: str
    model_name: str
    display_name: str
    description: str
    status: str
    capabilities: List[str]
    estimated_memory_mb: Optional[int] = None
    model_path: Optional[str] = None
    backend: Optional[str] = None
    loaded: bool = False


class ModelConfigRequest(BaseModel):
    provider: str
    backend: str
    model_path: str
    device: str = "cuda"
    config: Dict[str, Any] = {}


class ModelTestRequest(BaseModel):
    provider_type: str
    provider_name: str
    model_name: str
    test_input: Dict[str, Any] = {}


class ModelTestResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    capabilities_tested: List[str] = []


@router.get("/models", response_model=List[ModelInfo])
async def list_models(
    provider_type: Optional[str] = None,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> List[ModelInfo]:
    """List all available models."""
    ptype = None
    if provider_type:
        from app.models.provider import ProviderType
        try:
            ptype = ProviderType(provider_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    providers = provider_registry.list_providers(ptype)
    return providers


@router.get("/models/{provider_type}/{provider_name}/{model_name}", response_model=ModelInfo)
async def get_model(
    provider_type: str,
    provider_name: str,
    model_name: str,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> ModelInfo:
    """Get model details."""
    from app.models.provider import ProviderType
    
    try:
        ptype = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    provider = provider_registry.get_provider(ptype, provider_name, model_name)
    if not provider:
        raise HTTPException(status_code=404, detail="Model not found")
    
    metadata = provider.metadata
    config = provider_registry._provider_configs.get(provider_type, {})
    
    return ModelInfo(
        type=provider_type,
        provider_name=metadata.provider_name,
        model_name=metadata.model_name,
        display_name=f"{metadata.provider_name} - {metadata.model_name}",
        description=f"{metadata.provider_name} provider for {provider_type}",
        status="available" if provider.is_available() else "unavailable",
        capabilities=[c.name for c in provider.get_capabilities() if c.supported],
        estimated_memory_mb=provider_registry._estimate_memory(ptype, config),
        model_path=config.get("model_path") if isinstance(config, dict) else getattr(config, "model_path", None),
        backend=config.get("backend") if isinstance(config, dict) else getattr(config, "backend", None),
        loaded=metadata.loaded,
    )


@router.post("/models/test", response_model=ModelTestResponse)
async def test_model(
    request: ModelTestRequest,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> ModelTestResponse:
    """Test a model with sample input."""
    from app.models.provider import ProviderType
    
    try:
        ptype = ProviderType(request.provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {request.provider_type}")
    
    result = await provider_registry.test_provider(
        ptype, request.provider_name, request.model_name, request.test_input
    )
    
    return ModelTestResponse(**result)


@router.post("/models/{provider_type}/{provider_name}/{model_name}/load")
async def load_model(
    provider_type: str,
    provider_name: str,
    model_name: str,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> Dict[str, str]:
    """Load a model into memory."""
    from app.models.provider import ProviderType
    
    try:
        ptype = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    success = await provider_registry.load_provider(ptype, provider_name, model_name)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to load model")
    
    return {"message": "Model loaded successfully", "model": model_name}


@router.post("/models/{provider_type}/{provider_name}/{model_name}/unload")
async def unload_model(
    provider_type: str,
    provider_name: str,
    model_name: str,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> Dict[str, str]:
    """Unload a model from memory."""
    from app.models.provider import ProviderType
    
    try:
        ptype = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    success = await provider_registry.unload_provider(ptype, provider_name, model_name)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to unload model")
    
    return {"message": "Model unloaded successfully", "model": model_name}


@router.get("/models/capabilities/matrix")
async def get_capability_matrix(
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> Dict[str, Any]:
    """Get capability matrix for all providers."""
    matrix = provider_registry.get_capability_matrix()
    return matrix.matrix


@router.get("/models/capabilities/check")
async def check_capability(
    provider_type: str,
    provider_name: str,
    capability: str,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> Dict[str, bool]:
    """Check if a provider supports a capability."""
    from app.models.provider import ProviderType
    
    try:
        ptype = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    supported = provider_registry.is_capability_supported(ptype, provider_name, capability)
    
    return {"supported": supported}