"""
Pipeline Completion API endpoints for the Cinematic Video Studio.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from uuid import UUID

from app.services.pipeline_completion_service import (
    PipelineCompletionService, 
    PipelineState, 
    PipelineStage,
    get_pipeline_completion_service,
)
from app.services.youtube_source_handler import YouTubeSourceHandler
from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine


router = APIRouter()


class PipelineStartRequest(BaseModel):
    """Request to start the complete pipeline."""
    project_id: UUID
    source_url: str
    target_languages: List[str] = []
    providers: Dict[str, str] = {}
    auto_continue: bool = True


class PipelineStatusResponse(BaseModel):
    """Pipeline status response."""
    project_id: UUID
    current_stage: Optional[str] = None
    completed_stages: List[str] = []
    failed_stages: List[str] = []
    stage_results: Dict[str, Dict[str, Any]] = {}
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    auto_continue: bool = True
    target_languages: List[str] = []
    providers: Dict[str, str] = {}


class PipelineControlRequest(BaseModel):
    """Request to control pipeline execution."""
    action: str  # pause, resume, retry
    stage: Optional[str] = None


def get_pipeline_service() -> PipelineCompletionService:
    return get_pipeline_completion_service()


def get_youtube_handler() -> YouTubeSourceHandler:
    from app.main import app
    return app.state.youtube_handler


def get_project_manager() -> ProjectManager:
    from app.main import app
    return app.state.project_manager


def get_workflow_engine() -> WorkflowEngine:
    from app.main import app
    return app.state.workflow_engine


@router.post("/pipeline/start", response_model=PipelineStatusResponse)
async def start_pipeline(
    request: PipelineStartRequest,
    background_tasks: BackgroundTasks,
    pipeline_service: PipelineCompletionService = Depends(get_pipeline_service),
    youtube_handler: YouTubeSourceHandler = Depends(get_youtube_handler),
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
) -> PipelineStatusResponse:
    """Start the complete pipeline from a YouTube URL."""
    # Verify project exists
    try:
        project_manager.load_project(str(request.project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate YouTube URL
    if not youtube_handler.is_youtube_url(request.source_url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    # Start pipeline
    state = await pipeline_service.start_pipeline(
        project_id=request.project_id,
        source_url=request.source_url,
        target_languages=request.target_languages,
        providers=request.providers,
        auto_continue=request.auto_continue,
    )
    
    return PipelineStatusResponse(
        project_id=state.project_id,
        current_stage=state.current_stage.value if state.current_stage else None,
        completed_stages=[s.value for s in state.completed_stages],
        failed_stages=[s.value for s in state.failed_stages],
        stage_results=state.stage_results,
        started_at=state.started_at.isoformat() if state.started_at else None,
        completed_at=state.completed_at.isoformat() if state.completed_at else None,
        error=state.error,
        auto_continue=state.auto_continue,
        target_languages=state.target_languages,
        providers=state.providers,
    )


@router.get("/pipeline/{project_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    project_id: UUID,
    pipeline_service: PipelineCompletionService = Depends(get_pipeline_service),
) -> PipelineStatusResponse:
    """Get current pipeline status."""
    state = pipeline_service.get_pipeline_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline not found for project")
    
    return PipelineStatusResponse(
        project_id=state.project_id,
        current_stage=state.current_stage.value if state.current_stage else None,
        completed_stages=[s.value for s in state.completed_stages],
        failed_stages=[s.value for s in state.failed_stages],
        stage_results=state.stage_results,
        started_at=state.started_at.isoformat() if state.started_at else None,
        completed_at=state.completed_at.isoformat() if state.completed_at else None,
        error=state.error,
        auto_continue=state.auto_continue,
        target_languages=state.target_languages,
        providers=state.providers,
    )


@router.post("/pipeline/{project_id}/control")
async def control_pipeline(
    project_id: UUID,
    request: PipelineControlRequest,
    pipeline_service: PipelineCompletionService = Depends(get_pipeline_service),
) -> Dict[str, str]:
    """Control pipeline execution (pause, resume, retry)."""
    if request.action == "pause":
        success = pipeline_service.pause_pipeline(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return {"message": "Pipeline paused"}
    
    elif request.action == "resume":
        success = pipeline_service.resume_pipeline(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return {"message": "Pipeline resumed"}
    
    elif request.action == "retry":
        if not request.stage:
            raise HTTPException(status_code=400, detail="Stage required for retry")
        try:
            stage = PipelineStage(request.stage)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {request.stage}")
        
        success = pipeline_service.retry_failed_stage(project_id, stage)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot retry stage")
        return {"message": f"Stage {request.stage} queued for retry"}
    
    elif request.action == "stop":
        success = pipeline_service.stop_pipeline(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        return {"message": "Pipeline stopped"}
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")


@router.get("/pipeline/{project_id}/stages")
async def get_pipeline_stages(
    project_id: UUID,
    pipeline_service: PipelineCompletionService = Depends(get_pipeline_service),
) -> Dict[str, Any]:
    """Get all pipeline stages and their status."""
    state = pipeline_service.get_pipeline_state(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline not found for project")
    
    stages = []
    for stage in PipelineStage:
        stages.append({
            "stage": stage.value,
            "status": "completed" if stage in state.completed_stages else 
                       "failed" if stage in state.failed_stages else
                       "current" if stage == state.current_stage else
                       "pending",
            "dependencies": [d.value for d in STAGE_DEPENDENCIES.get(PipelineStage(stage), [])],
        })
    
    return {
        "project_id": str(project_id),
        "stages": stages,
        "current_stage": state.current_stage.value if state.current_stage else None,
        "progress": f"{len(state.completed_stages)}/{len(PipelineStage)}",
    }


@router.post("/pipeline/from-youtube")
async def start_pipeline_from_youtube(
    project_id: UUID,
    url: str,
    target_languages: List[str] = [],
    providers: Dict[str, str] = {},
    auto_continue: bool = True,
    background_tasks: BackgroundTasks = None,
    pipeline_service: PipelineCompletionService = Depends(get_pipeline_service),
    youtube_handler: YouTubeSourceHandler = Depends(get_youtube_handler),
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
) -> PipelineStatusResponse:
    """Convenience endpoint to start pipeline directly from YouTube URL."""
    request = PipelineStartRequest(
        project_id=project_id,
        source_url=url,
        target_languages=target_languages,
        providers=providers,
        auto_continue=auto_continue,
    )
    return await start_pipeline(request, background_tasks, pipeline_service, youtube_handler, project_manager, workflow_engine)