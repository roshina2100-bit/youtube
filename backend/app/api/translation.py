"""
Translation API endpoints for the Cinematic Video Studio.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.models.translation import SceneTranslation, SemanticReview, TranslationStatus, LanguageWorkspace
from app.core.config import get_settings


router = APIRouter()


class TranslationRequest(BaseModel):
    target_languages: List[str]
    provider: str = "local_python"
    model: str = "nllb-200-distilled-600M"


class SceneTranslationResponse(BaseModel):
    scene_id: str
    language: str
    version: str
    source_language: str
    narration: str
    dialogue: List[dict]
    character_names: dict
    location_name: str
    cultural_notes: str
    semantic_review: dict
    voice_prompts: dict
    status: str


class SemanticReviewRequest(BaseModel):
    provider: str = "local_python"
    model: str = "llama-3-8b-instruct"


class SemanticReviewResponse(BaseModel):
    reviewed: bool
    checks: List[dict]
    issues: List[str]
    flags: List[str]
    status: str
    notes: str


def get_project_manager():
    from app.main import app
    return app.state.project_manager


def get_workflow_engine():
    from app.main import app
    return app.state.workflow_engine


@router.post("/projects/{project_id}/translate")
async def translate_project(
    project_id: str,
    request: TranslationRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Translate all scenes for all target languages."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if scenes exist
    scenes = project_manager.load_scenes_index(project_dir)
    if not scenes:
        raise HTTPException(status_code=400, detail="No scenes found. Generate scenes first.")

    # Create translation job
    job = Job(
        project_id=project_id,
        type=JobType.TRANSLATION,
        input={
            "target_languages": request.target_languages,
            "provider": request.provider,
            "model": request.model,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": "Translation started", "target_languages": request.target_languages}


@router.get("/projects/{project_id}/languages", response_model=List[str])
async def list_languages(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """List all target languages for a project."""
    try:
        project = project_manager.load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    return project.target_languages


@router.get("/projects/{project_id}/languages/{language}", response_model=dict)
async def get_language_workspace(
    project_id: str,
    language: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get translation workspace for a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace = project_manager.load_translation(project_dir, language)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Translation workspace not found for {language}")

    return {
        "language": workspace.language,
        "scenes": {k: v.model_dump() for k, v in workspace.scenes.items()},
        "semantic_review": workspace.semantic_review.model_dump(),
        "voice_prompts": workspace.voice_prompts,
        "music_prompts": workspace.music_prompts,
        "status": workspace.status.value,
        "completed_scenes": workspace.completed_scenes,
        "total_scenes": workspace.total_scenes
    }


@router.get("/projects/{project_id}/languages/{language}/scenes/{scene_id}", response_model=SceneTranslationResponse)
async def get_scene_translation(
    project_id: str,
    language: str,
    scene_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get translation for a specific scene in a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace = project_manager.load_translation(project_dir, language)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Translation workspace not found for {language}")

    translation = workspace.get_scene_translation(scene_id)
    if not translation:
        raise HTTPException(status_code=404, detail=f"Translation not found for scene {scene_id} in {language}")

    return SceneTranslationResponse(**translation.model_dump())


@router.post("/projects/{project_id}/languages/{language}/scenes/{scene_id}/review")
async def review_translation(
    project_id: str,
    language: str,
    scene_id: str,
    request: SemanticReviewRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Perform semantic review of a translation."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create semantic review job
    job = Job(
        project_id=project_id,
        type=JobType.SEMANTIC_REVIEW,
        input={
            "scene_id": scene_id,
            "language": language,
            "provider": request.provider,
            "model": request.model,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": "Semantic review started"}


@router.post("/projects/{project_id}/languages/{language}/scenes/{scene_id}/approve")
async def approve_translation(
    project_id: str,
    language: str,
    scene_id: str,
    approved: bool = True,
    approved_by: str = "user",
    notes: str = "",
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Approve or reject a scene translation."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace = project_manager.load_translation(project_dir, language)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Translation workspace not found for {language}")

    translation = workspace.get_scene_translation(scene_id)
    if not translation:
        raise HTTPException(status_code=404, detail=f"Translation not found for scene {scene_id} in {language}")

    if approved:
        translation.semantic_review.status = TranslationStatus.APPROVED
        translation.semantic_review.reviewed = True
        translation.semantic_review.reviewed_by = approved_by
        translation.semantic_review.reviewed_at = __import__('datetime').datetime.utcnow()
        translation.semantic_review.notes = notes
    else:
        translation.semantic_review.status = TranslationStatus.REVIEW_REQUIRED
        translation.semantic_review.issues.append(notes)

    workspace.add_scene_translation(translation)
    project_manager.save_translation(project_dir, language, workspace)

    return {"message": "Translation approved" if approved else "Translation rejected", "approved": approved}


@router.get("/projects/{project_id}/languages/{language}/semantic-review")
async def get_semantic_review(
    project_id: str,
    language: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get semantic review summary for a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace = project_manager.load_translation(project_dir, language)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Translation workspace not found for {language}")

    return workspace.semantic_review.model_dump()


@router.get("/projects/{project_id}/languages/{language}/voice-prompts")
async def get_voice_prompts(
    project_id: str,
    language: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get voice prompts for a language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    workspace = project_manager.load_translation(project_dir, language)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Translation workspace not found for {language}")

    return {"voice_prompts": workspace.voice_prompts}