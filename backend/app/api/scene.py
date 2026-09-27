"""
Scene API endpoints for the Cinematic Video Studio.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.models.scene import Scene, SceneStatus, SceneGenerationRequest, ScenePromptRequest, SceneImageRequest, SceneVideoRequest
from app.core.config import get_settings


router = APIRouter()


class SceneResponse(BaseModel):
    scene_id: str
    act_id: str
    order: int
    title: str
    duration_seconds: float
    status: str
    current_version: str
    characters: List[str]
    location_id: Optional[str]
    visual_style: str
    has_video: bool
    has_audio: bool


class SceneDetailResponse(BaseModel):
    scene_id: str
    version: str
    act_id: str
    order: int
    title: str
    duration_seconds: float
    source_segments: List[str]
    narration: str
    dialogue: List[dict]
    characters: List[dict]
    location: dict
    action: str
    emotion: str
    camera: dict
    lens: dict
    framing: str
    movement: str
    lighting: dict
    atmosphere: str
    props: List[str]
    environment: str
    visual_style: str
    music: dict
    sound_effects: List[dict]
    prompts: dict
    images: List[str]
    video_path: Optional[str]
    audio_paths: dict


def get_project_manager():
    from app.main import app
    return app.state.project_manager


def get_workflow_engine():
    from app.main import app
    return app.state.workflow_engine


@router.get("/projects/{project_id}/scenes", response_model=List[SceneResponse])
async def list_scenes(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """List all scenes for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    scenes = project_manager.load_scenes_index(project_dir)
    return [SceneResponse(**s) for s in scenes]


@router.get("/projects/{project_id}/scenes/{scene_id}", response_model=SceneDetailResponse)
async def get_scene(
    project_id: str,
    scene_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get scene details by ID."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    scene = project_manager.load_scene(project_dir, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    return SceneDetailResponse(**scene.model_dump())


@router.post("/projects/{project_id}/scenes/generate")
async def generate_scenes(
    project_id: str,
    provider: str = "local_python",
    model: str = "llama-3-8b-instruct",
    background_tasks: BackgroundTasks = None,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate cinematic scenes from story graph."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    story = project_manager.load_story(project_dir)
    if not story:
        raise HTTPException(status_code=400, detail="Story not analyzed yet")

    # Create scene generation job
    job = Job(
        project_id=project_id,
        type=JobType.SCENE_GENERATION,
        input={"provider": provider, "model": model},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Scene generation started"}


@router.post("/projects/{project_id}/scenes/{scene_id}/generate-prompts")
async def generate_scene_prompts(
    project_id: str,
    scene_id: str,
    provider: str = "local_python",
    model: str = "llama-3-8b-instruct",
    background_tasks: BackgroundTasks = None,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate all cinematic prompts for a scene."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    scene = project_manager.load_scene(project_dir, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Create prompt generation job
    job = Job(
        project_id=project_id,
        type=JobType.SCENE_PROMPT_GEN,
        input={"scene_id": scene_id, "provider": provider, "model": model},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Scene prompt generation started"}


@router.post("/projects/{project_id}/scenes/{scene_id}/generate-image")
async def generate_scene_image(
    project_id: str,
    scene_id: str,
    prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    width: int = 1920,
    height: int = 1080,
    seed: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate scene keyframe image."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    scene = project_manager.load_scene(project_dir, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Create image generation job
    job = Job(
        project_id=project_id,
        type=JobType.IMAGE_GENERATION,
        input={
            "scene_id": scene_id,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "seed": seed,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": "Scene image generation started"}


@router.post("/projects/{project_id}/scenes/{scene_id}/generate-video")
async def generate_scene_video(
    project_id: str,
    scene_id: str,
    image_path: str,
    prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    num_frames: int = 25,
    fps: int = 7,
    background_tasks: BackgroundTasks = None,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate scene video from image."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    scene = project_manager.load_scene(project_dir, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    # Create video generation job
    job = Job(
        project_id=project_id,
        type=JobType.VIDEO_GENERATION,
        input={
            "scene_id": scene_id,
            "image_path": image_path,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_frames": num_frames,
            "fps": fps,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": "Scene video generation started"}


@router.post("/projects/{project_id}/scenes/generate-silent-master")
async def generate_silent_master(
    project_id: str,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate silent master video by concatenating all scene videos."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create silent master job
    job = Job(
        project_id=project_id,
        type=JobType.SILENT_MASTER,
        input={},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Silent master generation started"}


@router.get("/projects/{project_id}/scenes/{scene_id}/prompts")
async def get_scene_prompts(
    project_id: str,
    scene_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get all prompts for a scene."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    scene = project_manager.load_scene(project_dir, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    return scene.prompts.model_dump()


@router.get("/projects/{project_id}/scenes/{scene_id}/images")
async def get_scene_images(
    project_id: str,
    scene_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get all generated images for a scene."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    scene = project_manager.load_scene(project_dir, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    return {"images": scene.images}