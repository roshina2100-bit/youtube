"""
Transcript API endpoints for the Cinematic Video Studio.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.models.transcript import TranscriptData, TranscriptSegment, LanguageDetectionResult, TranscriptImportRequest, TranscriptNormalizeRequest
from app.core.config import get_settings
from app.core.security import validate_project_path, sanitize_filename, validate_file_extension


router = APIRouter()

TRANSCRIPT_EXTENSIONS = {'.txt', '.srt', '.vtt', '.json'}


class TranscriptSegmentResponse(BaseModel):
    id: str
    start: float
    end: float
    text: str
    speaker: Optional[str] = None
    language: Optional[str] = None
    confidence: float = 1.0


class TranscriptResponse(BaseModel):
    segments: List[TranscriptSegmentResponse]
    speakers: List[dict]
    total_duration: float
    language: str
    normalized: bool


class LanguageDetectionResponse(BaseModel):
    detected_language: str
    confidence: float
    detector: str
    alternatives: List[dict]
    manual_override: bool


def get_project_manager():
    from app.main import app
    return app.state.project_manager


def get_workflow_engine():
    from app.main import app
    return app.state.workflow_engine


@router.post("/projects/{project_id}/transcript/import")
async def import_transcript(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Form(None),
    format: str = Form("txt"),
    language: Optional[str] = Form(None),
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Import transcript from file or raw content."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    transcript_dir = project_dir / "transcript"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    if file:
        filename = sanitize_filename(file.filename)
        if not validate_file_extension(filename, list({'.txt', '.srt', '.vtt', '.json'})):
            raise HTTPException(status_code=400, detail=f"Unsupported format. Allowed: {', '.join({'.txt', '.srt', '.vtt', '.json'})}")

        file_path = transcript_dir / "original.txt"
        content_bytes = await file.read()
        file_path.write_bytes(content_bytes)
        content = content_bytes.decode('utf-8', errors='replace')
    elif content:
        file_path = transcript_dir / "original.txt"
        file_path.write_text(content, encoding='utf-8')
    else:
        raise HTTPException(status_code=400, detail="Either file or content required")

    # Save original
    (transcript_dir / "original.json").write_text(
        '{"content": ' + __import__('json').dumps(content) + ', "format": "' + format + '"}',
        encoding='utf-8'
    )

    # Create transcript processing job
    from app.models.job import Job, JobType
    job = Job(
        project_id=project_id,
        type=JobType.TRANSCRIPT_PROCESS,
        input={"file_path": "transcript/original.txt", "format": format, "language": language},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Transcript imported successfully", "file_path": "transcript/original.txt"}


@router.get("/projects/{project_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get normalized transcript for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    transcript = project_manager.load_transcript(project_dir)
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found")

    return TranscriptResponse(
        segments=[TranscriptSegmentResponse(**s.model_dump()) for s in transcript.segments],
        speakers=transcript.speakers,
        total_duration=transcript.total_duration,
        language=transcript.language,
        normalized=transcript.normalized
    )


@router.get("/projects/{project_id}/transcript/raw")
async def get_raw_transcript(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get raw transcript text."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    transcript = project_manager.load_transcript(project_dir)
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found")

    return {"text": transcript.get_text(include_timestamps=True)}


@router.post("/projects/{project_id}/transcript/normalize")
async def normalize_transcript(
    project_id: str,
    request: TranscriptNormalizeRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Normalize transcript (clean up, fix punctuation, etc.)."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create normalization job
    from app.models.job import Job, JobType
    job = Job(
        project_id=project_id,
        type=JobType.TRANSCRIPT_PROCESS,
        input={"action": "normalize", "options": request.model_dump()},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Transcript normalization started"}


@router.post("/projects/{project_id}/transcript/detect-language")
async def detect_language(
    project_id: str,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Detect language of transcript."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create language detection job
    from app.models.job import Job, JobType
    job = Job(
        project_id=project_id,
        type=JobType.LANGUAGE_DETECT,
        input={},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Language detection started"}


@router.get("/projects/{project_id}/transcript/language", response_model=LanguageDetectionResponse)
async def get_language_detection(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get language detection results."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    detection = project_manager.load_language_detection(project_dir)
    if not detection:
        raise HTTPException(status_code=404, detail="Language detection not performed")

    return LanguageDetectionResponse(**detection.model_dump())


@router.post("/projects/{project_id}/transcript/language/override")
async def override_language(
    project_id: str,
    language: str = Form(...),
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Manually override detected language."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    detection = project_manager.load_language_detection(project_dir)
    if not detection:
        raise HTTPException(status_code=404, detail="Language detection not performed")

    detection.detected_language = language
    detection.manual_override = True
    detection.confidence = 1.0

    # Save updated detection
    import json
    detection_path = project_dir / "transcript" / "language_detection.json"
    detection_path.write_text(json.dumps(detection.model_dump(mode='json'), indent=2), encoding='utf-8')

    # Update project manifest
    project = project_manager.load_project(project_id)
    project.source_language = language
    project.source_language_confidence = 1.0
    project.source_language_detector = "manual_override"
    project_manager.save_project(project_dir, project)

    return {"message": "Language overridden successfully", "language": language}


@router.get("/projects/{project_id}/transcript/segments")
async def get_transcript_segments(
    project_id: str,
    start: float = 0,
    end: Optional[float] = None,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get transcript segments within time range."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    transcript = project_manager.load_transcript(project_dir)
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found")

    segments = transcript.get_segments_in_range(start, end or float('inf'))
    return {"segments": [s.model_dump() for s in segments]}