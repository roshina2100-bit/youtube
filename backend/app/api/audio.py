"""
Audio API endpoints for the Cinematic Video Studio.
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


class TTSGenerateRequest(BaseModel):
    scene_id: str
    language: str
    provider: str = "local_ppython"
    model: str = "xtts-v2"


class MusicGenerateRequest(BaseModel):
    scene_id: str
    language: str
    provider: str = "local_python"
    model: str = "musicgen-large"


class SFXGenerateRequest(BaseModel):
    scene_id: str
    language: str
    provider: str = "local_python"
    model: str = "audioldm2"


class AudioMixRequest(BaseModel):
    language: str


def get_project_manager():
    from app.main import app
    return app.state.project_manager


def get_workflow_engine():
    from app.main import app
    return app.state.workflow_engine


@router.post("/projects/{project_id}/audio/tts")
async def generate_tts(
    project_id: str,
    request: TTSGenerateRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate TTS audio for a scene in a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create TTS job
    job = Job(
        project_id=project_id,
        type=JobType.TTS_GENERATION,
        input={
            "scene_id": request.scene_id,
            "language": request.language,
            "provider": request.provider,
            "model": request.model,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": "TTS generation started"}


@router.post("/projects/{project_id}/audio/music")
async def generate_music(
    project_id: str,
    request: MusicGenerateRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate music for a scene in a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create music generation job
    job = Job(
        project_id=project_id,
        type=JobType.MUSIC_GENERATION,
        input={
            "scene_id": request.scene_id,
            "language": request.language,
            "provider": request.provider,
            "model": request.model,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": "Music generation started"}


@router.post("/projects/{project_id}/audio/sfx")
async def generate_sfx(
    project_id: str,
    request: SFXGenerateRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate sound effects for a scene in a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create SFX generation job
    job = Job(
        project_id=project_id,
        type=JobType.SFX_GENERATION,
        input={
            "scene_id": request.scene_id,
            "language": request.language,
            "provider": request.provider,
            "model": request.model,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": "SFX generation started"}


@router.post("/projects/{project_id}/audio/mix")
async def mix_audio(
    project_id: str,
    request: AudioMixRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Mix all audio tracks for a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create audio mixing job
    job = Job(
        project_id=project_id,
        type=JobType.AUDIO_MIXING,
        input={"language": request.language},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Audio mixing started"}


@router.get("/projects/{project_id}/audio/{language}")
async def get_language_audio(
    project_id: str,
    language: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get audio files for a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    audio_dir = project_dir / "audio" / language
    if not audio_dir.exists():
        raise HTTPException(status_code=404, detail=f"No audio found for {language}")

    audio_files = {}
    for subdir in ["narration", "dialogue", "music", "sfx"]:
        subdir_path = audio_dir / subdir
        if subdir_path.exists():
            audio_files[subdir] = [f.name for f in subdir_path.iterdir() if f.is_file()]

    master_path = audio_dir / "master_audio.wav"
    if master_path.exists():
        audio_files["master"] = "master_audio.wav"

    return {"language": language, "audio_files": audio_files}


@router.get("/projects/{project_id}/audio/{language}/master")
async def get_master_audio(
    project_id: str,
    language: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get master audio file for a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    master_path = project_dir / "audio" / language / "master_audio.wav"
    if not master_path.exists():
        raise HTTPException(status_code=404, detail=f"Master audio not found for {language}")

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(master_path),
        filename=f"{language}_master_audio.wav",
        media_type="audio/wav"
    )