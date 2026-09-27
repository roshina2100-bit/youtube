"""
Render API endpoints for the Cinematic Video Studio.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.core.config import get_settings


router = APIRouter()


class RenderRequest(BaseModel):
    language: str
    include_subtitles: bool = True
    subtitle_style: Optional[str] = None


class ExportRequest(BaseModel):
    format: str = "zip"  # zip, tar.gz
    include_types: List[str] = []  # empty = all
    languages: List[str] = []  # empty = all
    approved_only: bool = True


def get_project_manager():
    from app.main import app
    return app.state.project_manager


def get_workflow_engine():
    from app.main import app
    return app.state.workflow_engine


@router.post("/projects/{project_id}/render")
async def render_final_video(
    project_id: str,
    request: RenderRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Render final video for a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if silent master exists
    from app.services.scene_service import SceneService
    scene_service = SceneService(project_manager, workflow_engine.provider_registry)
    silent_master = scene_service.get_silent_master(project_id)
    if not silent_master:
        raise HTTPException(status_code=400, detail="Silent master not generated yet")

    # Check if master audio exists for language
    master_audio_path = project_dir / "audio" / request.language / "master_audio.wav"
    if not master_audio_path.exists():
        raise HTTPException(status_code=400, detail=f"Master audio not found for {request.language}")

    # Create final render job
    job = Job(
        project_id=project_id,
        type=JobType.FINAL_RENDER,
        input={
            "language": request.language,
            "include_subtitles": request.include_subtitles,
            "subtitle_style": request.subtitle_style,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": f"Final render started for {request.language}"}


@router.post("/projects/{project_id}/render/all")
async def render_all_languages(
    project_id: str,
    background_tasks: BackgroundTasks,
    include_subtitles: bool = True,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Render final videos for all target languages."""
    try:
        project = project_manager.load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create render jobs for all languages
    for language in project.target_languages:
        job = Job(
            project_id=project_id,
            type=JobType.FINAL_RENDER,
            input={
                "language": language,
                "include_subtitles": include_subtitles,
            },
        )
        await workflow_engine.submit_job(job)

    return {"message": f"Final render started for {len(project.target_languages)} languages"}


@router.get("/projects/{project_id}/output")
async def list_outputs(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """List all rendered output videos."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    output_dir = project_dir / "output"
    if not output_dir.exists():
        return {"outputs": []}

    outputs = []
    for lang_dir in output_dir.iterdir():
        if lang_dir.is_dir():
            final_video = lang_dir / "final.mp4"
            if final_video.exists():
                stat = final_video.stat()
                outputs.append({
                    "language": lang_dir.name,
                    "path": f"output/{lang_dir.name}/final.mp4",
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime
                })

    return {"outputs": outputs}


@router.get("/projects/{project_id}/output/{language}")
async def get_output_video(
    project_id: str,
    language: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get final rendered video for a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    video_path = project_dir / "output" / language / "final.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Output video not found for {language}")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(video_path),
        filename=f"{language}_final.mp4",
        media_type="video/mp4"
    )


@router.post("/projects/{project_id}/export")
async def export_project(
    project_id: str,
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Export project as package."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create export job
    job = Job(
        project_id=project_id,
        type=JobType.EXPORT,
        input=request.model_dump(),
    )
    await workflow_engine.submit_job(job)

    return {"message": "Project export started"}


@router.get("/projects/{project_id}/exports")
async def list_exports(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """List all export packages for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    exports_dir = project_dir / "exports"
    if not exports_dir.exists():
        return {"exports": []}

    exports = []
    for export_file in exports_dir.iterdir():
        if export_file.is_file():
            stat = export_file.stat()
            exports.append({
                "filename": export_file.name,
                "path": f"exports/{export_file.name}",
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime
            })

    return {"exports": exports}


@router.get("/projects/{project_id}/exports/{filename}")
async def download_export(
    project_id: str,
    filename: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Download export package."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    export_path = project_dir / "exports" / filename
    if not export_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(export_path),
        filename=filename,
        media_type="application/zip"
    )