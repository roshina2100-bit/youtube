"""
Health check API endpoints.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.core.config import get_settings
from app.providers.registry import ProviderRegistry


router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    from datetime import datetime
    settings = get_settings()
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat() + "Z",
        services={
            "api": "running",
            "database": "file-based",
            "providers": "initialized",
        }
    )


@router.get("/health/detailed")
async def detailed_health() -> Dict[str, Any]:
    """Detailed health check with provider status."""
    settings = get_settings()
    
    # Check provider registry
    # This would be injected in real implementation
    provider_status = {}
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp:": datetime.utcnow().isoformat() + "Z",
        "settings": {
            "project_root": settings.project_root,
            "debug": settings.debug,
            "max_concurrent_gpu_jobs": settings.max_concurrent_gpu_jobs,
        },
        "providers": provider_status,
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, str]:
    """Kubernetes readiness probe."""
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "alive"}