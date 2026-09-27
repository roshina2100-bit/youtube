"""
Character API endpoints for the Cinematic Video Studio.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.models.character import CharacterBible, CharacterStatus, CharacterVersion, CharacterPromptRequest, CharacterImageRequest, CharacterApprovalRequest, CharacterUploadReferenceRequest
from app.core.config import get_settings
from app.core.security import validate_project_path, sanitize_filename, validate_file_extension


router = APIRouter()

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}


class CharacterResponse(BaseModel):
    character_id: str
    canonical_name: str
    aliases: List[str]
    role: str
    importance: str
    status: str
    current_version: str
    approved_version: Optional[str]
    reference_image: Optional[str]
    scenes: List[str]


class CharacterVersionResponse(BaseModel):
    version: str
    prompt: str
    negative_prompt: str
    image_path: Optional[str]
    created_at: str
    approved: bool
    approved_at: Optional[str]


class CharacterImageGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None


def get_project_manager():
    from app.main import app
    return app.state.project_manager


def get_workflow_engine():
    from app.main import app
    return app.state.workflow_engine


@router.get("/projects/{project_id}/characters", response_model=List[CharacterResponse])
async def list_characters(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """List all characters for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    characters = project_manager.load_characters_index(project_dir)
    return [CharacterResponse(**c) for c in characters]


@router.get("/projects/{project_id}/characters/{character_id}", response_model=dict)
async def get_character(
    project_id: str,
    character_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get character bible by ID."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    character = project_manager.load_character(project_dir, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    return character.model_dump()


@router.post("/projects/{project_id}/characters/{character_id}/generate-prompt")
async def generate_character_prompt(
    project_id: str,
    character_id: str,
    provider: str = "local_python",
    model: str = "llama-3-8b-instruct",
    background_tasks: BackgroundTasks = None,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate character image prompt."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    character = project_manager.load_character(project_dir, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Create prompt generation job
    job = Job(
        project_id=project_id,
        type=JobType.CHARACTER_PROMPT_GEN,
        input={"character_id": character_id, "provider": provider, "model": model},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Character prompt generation started"}


@router.post("/projects/{project_id}/characters/{character_id}/generate-image")
async def generate_character_image(
    project_id: str,
    character_id: str,
    request: CharacterImageGenerateRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Generate character image."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    character = project_manager.load_character(project_dir, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Get current version
    version = character.current_version
    version_data = character.versions.get(version)
    if not version_data:
        raise HTTPException(status_code=400, detail="No current version found")

    # Create image generation job
    job = Job(
        project_id=project_id,
        type=JobType.CHARACTER_IMAGE_GEN,
        input={
            "character_id": character_id,
            "version": version,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
            "seed": request.seed,
        },
    )
    await workflow_engine.submit_job(job)

    return {"message": "Character image generation started"}


@router.post("/projects/{project_id}/characters/{character_id}/approve")
async def approve_character(
    project_id: str,
    character_id: str,
    request: CharacterApprovalRequest,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Approve or reject a character version."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    character = project_manager.load_character(project_dir, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    success = character.approve_version(request.version, request.approved_by)
    if not success:
        raise HTTPException(status_code=400, detail="Version not found")

    if request.approved:
        character.lock_character()

    project_manager.save_character(project_dir, character)

    return {"message": "Character approved" if request.approved else "Character rejected", "approved": request.approved}


@router.post("/projects/{project_id}/characters/{character_id}/upload-reference")
async def upload_reference_image(
    project_id: str,
    character_id: str,
    version: str = Form(...),
    file: UploadFile = File(...),
    set_as_canonical: bool = Form(False),
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Upload a reference image for a character."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    character = project_manager.load_character(project_dir, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Validate file
    filename = sanitize_filename(file.filename)
    if not validate_file_extension(filename, list(IMAGE_EXTENSIONS)):
        raise HTTPException(status_code=400, detail=f"Unsupported image format. Allowed: {', '.join(IMAGE_EXTENSIONS)}")

    # Save to references folder
    ref_dir = project_dir / "characters" / character_id / "references"
    ref_dir.mkdir(parents=True, exist_ok=True)

    version_num = project_manager.get_next_version(project_dir, f"{character_id}_ref", "characters/references")
    ext = Path(filename).suffix
    ref_filename = f"ref_{version_num}{ext}"
    ref_path = ref_dir / ref_filename

    content = await file.read()
    ref_path.write_bytes(content)

    # Update version data
    version_data = character.versions.get(version)
    if version_data:
        version_data.reference_image_path = f"characters/{character_id}/references/{ref_filename}"
        character.add_version(version_data)

    if set_as_canonical:
        # Copy to approved folder
        approved_dir = project_dir / "characters" / character_id / "approved"
        approved_dir.mkdir(parents=True, exist_ok=True)
        canonical_path = approved_dir / "reference.png"
        import shutil
        shutil.copy2(ref_path, canonical_path)

        character.reference_image = f"characters/{character_id}/approved/reference.png"
        character.approved_version = version
        character.status = CharacterStatus.APPROVED

    project_manager.save_character(project_dir, character)

    return {"message": "Reference image uploaded", "reference_path": f"characters/{character_id}/references/{ref_filename}"}


@router.get("/projects/{project_id}/characters/{character_id}/versions")
async def get_character_versions(
    project_id: str,
    character_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get all versions of a character."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    character = project_manager.load_character(project_dir, character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    versions = []
    for ver, data in character.versions.items():
        versions.append(CharacterVersionResponse(
            version=ver,
            prompt=data.prompt,
            negative_prompt=data.negative_prompt,
            image_path=data.image_path,
            created_at=data.created_at.isoformat() if data.created_at else "",
            approved=data.approved,
            approved_at=data.approved_at.isoformat() if data.approved_at else None
        ))

    return {"versions": versions}