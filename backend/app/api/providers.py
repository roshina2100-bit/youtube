"""
Providers API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.providers.registry import ProviderRegistry
from app.models.provider import ProviderType, ProviderCapability, ProviderInfo


router = APIRouter()


def get_provider_registry() -> ProviderRegistry:
    from app.main import app
    return app.state.provider_registry


class ProviderListResponse(BaseModel):
    providers: List[ProviderInfo]
    total: int


class CapabilityMatrixResponse(BaseModel):
    matrix: Dict[str, Dict[str, Dict[str, bool]]]


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    provider_type: Optional[str] = None,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> ProviderListResponse:
    """List all registered providers."""
    ptype = None
    if provider_type:
        try:
            ptype = ProviderType(provider_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    providers = provider_registry.list_providers(ptype)
    return ProviderListResponse(providers=providers, total=len(providers))


@router.get("/providers/capabilities", response_model=CapabilityMatrixResponse)
async def get_capabilities(
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> CapabilityMatrixResponse:
    """Get capability matrix for all providers."""
    matrix = provider_registry.get_capability_matrix()
    return CapabilityMatrixResponse(matrix=matrix.matrix)


@router.get("/providers/capabilities/check")
async def check_capability(
    provider_type: str,
    provider_name: str,
    capability: str,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> Dict[str, bool]:
    """Check if a provider supports a capability."""
    try:
        ptype = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    supported = provider_registry.is_capability_supported(ptype, provider_name, capability)
    return {"supported": supported}


@router.get("/providers/supported")
async def get_supported_providers(
    provider_type: str,
    capability: str,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> Dict[str, List[str]]:
    """Get providers that support a capability."""
    try:
        ptype = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    providers = provider_registry.get_supported_providers(ptype, capability)
    return {"providers": providers}


@router.get("/providers/{provider_type}/{provider_name}/{model_name}")
async def get_provider_info(
    provider_type: str,
    provider_name: str,
    model_name: str,
    provider_registry: ProviderRegistry = Depends(get_provider_registry),
) -> Dict[str, Any]:
    """Get detailed provider information."""
    try:
        ptype = ProviderType(provider_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider type: {provider_type}")
    
    provider = provider_registry.get_provider(ptype, provider_name, model_name)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    metadata = provider.metadata
    capabilities = provider.get_capabilities()
    
    return {
        "metadata": metadata.model_dump(),
        "capabilities": [c.model_dump() for c in capabilities],
        "available": provider.is_available(),
    }