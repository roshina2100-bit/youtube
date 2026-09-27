"""
Source media API endpoints for the Cinematic Video Studio.
"""

import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType, JobStatus
from app.core.config import get_settings
from app.core.security import validate_project_path, sanitize_filename, validate_file_extension, validate_mime_type


router = APIRouter()


# Allowed media extensions
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.aac', '.m4a', '.wma'}
TRANSCRIPT_EXTENSIONS = {'.txt', '.srt', '.vtt', '.json'}
ALL_MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | TRANSCRIPT_EXTENSIONS


class SourceImportRequest(BaseModel):
    """Request to import source media."""
    source_type: str = "local_file"  # local_file, url, transcript, youtube
    url: Optional[str] = None
    language: Optional[str] = None
    download_video: bool = True
    download_transcript: bool = True
    quality: str = "best[height<=1080]"


class SourceInfoResponse(BaseModel):
    """Source media information response."""
    type: str
    path: str
    original_filename: str
    duration_seconds: float
    metadata: dict


def get_project_manager() -> ProjectManager:
    from app.main import app
    return app.state.project_manager


def get_workflow_engine() -> WorkflowEngine:
    from app.main import app
    return app.state.workflow_engine


@router.post("/projects/{project_id}/source", response_model=SourceInfoResponse)
async def import_source(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    source_type: str = Form("local_file"),
    url: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
) -> SourceInfoResponse:
    """Import source media (video, audio, or transcript) for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    source_dir = project_dir / "source" / "source_media"
    source_dir.mkdir(parents=True, exist_ok=True)

    if source_type == "local_file":
        if not file:
            raise HTTPException(status_code=400, detail="File required for local_file source type")

        # Validate file
        filename = sanitize_filename(file.filename)
        if not validate_file_extension(filename, list(ALL_MEDIA_EXTENSIONS)):
            raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(ALL_MEDIA_EXTENSIONS)}")

        # Save file
        file_path = source_dir / filename
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        # Probe media for metadata
        from app.utils.ffmpeg import FFmpegWrapper
        ffmpeg = FFmpegWrapper(get_settings().ffmpeg_path)
        try:
            metadata = await ffmpeg.probe(str(file_path))
            video_info = await ffmpeg.get_video_info(str(file_path))
            audio_info = await ffmpeg.get_audio_info(str(file_path))
            duration = video_info.get("duration") or audio_info.get("duration") or 0
        except Exception:
            metadata = {}
            duration = 0

        # Update project manifest
        project = project_manager.load_project(project_id)
        project.source = {
            "type": "local_file",
            "path": f"source/source_media/{filename}",
            "original_filename": file.filename,
            "duration_seconds": duration,
            "metadata": metadata
        }
        project_manager.save_project(project_dir, project)

        # Create source import job
        job = Job(
            project_id=project_id,
            type=JobType.SOURCE_IMPORT,
            input={"file_path": f"source/source_media/{filename}", "source_type": "local_file"},
        )
        await workflow_engine.submit_job(job)

        return SourceInfoResponse(
            type="local_file",
            path=f"source/source_media/{filename}",
            original_filename=file.filename,
            duration_seconds=duration,
            metadata=metadata
        )

    elif source_type == "youtube":
        if not url:
            raise HTTPException(status_code=400, detail="URL required for youtube source type")
        
        # Import YouTube URL using the YouTube handler
        from app.services.youtube_source_handler import YouTubeSourceHandler
        youtube_handler = YouTubeSourceHandler(project_manager, workflow_engine)
        
        try:
            result = await youtube_handler.import_youtube_url(
                project_id=project_id,
                url=url,
                download_video=True,
                download_transcript=True,
                quality="best[height<=1080]",
            )
            
            return SourceInfoResponse(
                type="youtube",
                path=result.get("video_path", ""),
                original_filename=result.get("title", "youtube_video"),
                duration_seconds=result.get("duration_seconds", 0),
                metadata=result.get("metadata", {})
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to import YouTube URL: {str(e)}")

    elif source_type == "transcript":
        if not file:
            raise HTTPException(status_code=400, detail="Transcript file required")

        filename = sanitize_filename(file.filename)
        if not validate_file_extension(filename, list(TRANSCRIPT_EXTENSIONS)):
            raise HTTPException(status_code=400, detail=f"Unsupported transcript format. Allowed: {', '.join(TRANSCRIPT_EXTENSIONS)}")

        transcript_dir = project_dir / "transcript"
        transcript_dir.mkdir(parents=True, exist_ok=True)

        file_path = transcript_dir / "original.txt"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Update project
        project = project_manager.load_project(project_id)
        project.source = {
            "type": "transcript",
            "path": "transcript/original.txt",
            "original_filename": file.filename,
            "duration_seconds": 0,
            "metadata": {}
        }
        project_manager.save_project(project_dir, project)

        # Create transcript processing job
        job = Job(
            project_id=project_id,
            type=JobType.TRANSCRIPT_PROCESS,
            input={"file_path": "transcript/original.txt"},
        )
        await workflow_engine.submit_job(job)

        return SourceInfoResponse(
            type="transcript",
            path="transcript/original.txt",
            original_filename=file.filename,
            duration_seconds=0,
            metadata={}
        )

    else:
        raise HTTPException(status_code=400, detail=f"Unknown source type: {source_type}")


@router.get("/projects/{project_id}/source", response_model=SourceInfoResponse)
async def get_source_info(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> SourceInfoResponse:
    """Get source media information for a project."""
    try:
        project = project_manager.load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    source = project.source
    return SourceInfoResponse(
        type=source.get("type", ""),
        path=source.get("path", ""),
        original_filename=source.get("original_filename", ""),
        duration_seconds=source.get("duration_seconds", 0),
        metadata=source.get("metadata", {})
    )


@router.get("/projects/{project_id}/source/download")
async def download_source(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Download the source media file."""
    try:
        project = project_manager.load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    source_path = project.source.get("path")
    if not source_path:
        raise HTTPException(status_code=404, detail="No source media found")

    project_dir = project_manager.get_project_path(project_id)
    full_path = project_dir / source_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found on disk")

    return FileResponse(
        path=str(full_path),
        filename=project.source.get("original_filename", "source"),
        media_type="application/octet-stream"
    )


@router.delete("/projects/{project_id}/source")
async def delete_source(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Delete source media from project."""
    try:
        project = project_manager.load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    source_path = project.source.get("path")
    if source_path:
        project_dir = project_manager.get_project_path(project_id)
        full_path = project_dir / source_path
        if full_path.exists():
            full_path.unlink()

    # Reset source in project
    project.source = {
        "type": "",
        "path": "",
        "original_filename": "",
        "duration_seconds": 0,
        "metadata": {}
    }
    project_manager.save_project(project_dir, project)

    return {"message": "Source media deleted"}