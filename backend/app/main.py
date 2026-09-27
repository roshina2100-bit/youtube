"""
Cinematic Multi-Language Video Studio - FastAPI Backend
Main application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api import projects, models, providers, jobs, health, source, transcript, story, character, scene, translation, audio, render, pipeline
from app.services.project_manager import ProjectManager
from app.services.youtube_source_handler import YouTubeSourceHandler
from app.services.pipeline_completion_service import PipelineCompletionService
from app.providers.registry import ProviderRegistry
from app.workflow.engine import WorkflowEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    
    # Setup logging
    setup_logging(settings.log_level, settings.debug)
    
    # Initialize core services
    app.state.project_manager = ProjectManager(settings.project_root)
    app.state.provider_registry = ProviderRegistry()
    app.state.workflow_engine = WorkflowEngine(
        app.state.project_manager,
        app.state.provider_registry
    )
    
    # Initialize YouTube handler
    app.state.youtube_handler = YouTubeSourceHandler(
        app.state.project_manager,
        app.state.workflow_engine
    )
    
    # Initialize pipeline completion service
    app.state.pipeline_completion_service = PipelineCompletionService(
        app.state.project_manager,
        app.state.workflow_engine,
        app.state.youtube_handler
    )
    
    # Load providers
    await app.state.provider_registry.initialize(settings)
    
    # Start workflow engine
    await app.state.workflow_engine.start()
    
    yield
    
    # Cleanup
    await app.state.workflow_engine.stop()
    await app.state.provider_registry.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Cinematic Multi-Language Video Studio",
        description="Local-first cinematic video production system",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
    app.include_router(models.router, prefix="/api/v1", tags=["models"])
    app.include_router(providers.router, prefix="/api/v1", tags=["providers"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(source.router, prefix="/api/v1", tags=["source"])
    app.include_router(transcript.router, prefix="/api/v1", tags=["transcript"])
    app.include_router(story.router, prefix="/api/v1", tags=["story"])
    app.include_router(character.router, prefix="/api/v1", tags=["character"])
    app.include_router(scene.router, prefix="/api/v1", tags=["scene"])
    app.include_router(translation.router, prefix="/api/v1", tags=["translation"])
    app.include_router(audio.router, prefix="/api/v1", tags=["audio"])
    app.include_router(render.router, prefix="/api/v1", tags=["render"])
    app.include_router(pipeline.router, prefix="/api/v1", tags=["pipeline"])
    
    # Static files for generated assets (development only)
    if settings.debug:
        app.mount("/assets", StaticFiles(directory=settings.project_root), name="assets")
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )