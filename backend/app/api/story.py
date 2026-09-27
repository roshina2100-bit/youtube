"""
Story API endpoints for the Cinematic Video Studio.
"""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.models.job import Job, JobType
from app.models.story import StoryGraph, Act, Event, Theme, CharacterRef, LocationRef, Relationship, CulturalContext
from app.core.config import get_settings


router = APIRouter()


class StoryAnalysisRequest(BaseModel):
    provider: str = "local_python"
    model: str = "llama-3-8b-instruct"


class StoryResponse(BaseModel):
    story_id: str
    title: str
    summary: str
    source_language: str
    acts: List[dict]
    characters: List[dict]
    locations: List[dict]
    events: List[dict]
    themes: List[dict]
    relationships: List[dict]
    cultural_context: dict


def get_project_manager():
    from app.main import app
    return app.state.project_manager


def get_workflow_engine():
    from app.main import app
    return app.state.workflow_engine


@router.post("/projects/{project_id}/analyze-story")
async def analyze_story(
    project_id: str,
    request: StoryAnalysisRequest,
    background_tasks: BackgroundTasks,
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Analyze transcript and generate story graph."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if transcript exists
    transcript = project_manager.load_transcript(project_dir)
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript found. Process transcript first.")

    # Create story analysis job
    job = Job(
        project_id=project_id,
        type=JobType.STORY_ANALYSIS,
        input={"provider": request.provider, "model": request.model},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Story analysis started"}


@router.get("/projects/{project_id}/story", response_model=StoryResponse)
async def get_story(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get story graph for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    story = project_manager.load_story(project_dir)
    if not story:
        raise HTTPException(status_code=404, detail="Story not analyzed yet")

    return StoryResponse(
        story_id=str(story.story_id),
        title=story.title,
        summary=story.summary,
        source_language=story.source_language,
        acts=[a.model_dump() for a in story.acts],
        characters=[c.model_dump() for c in story.characters],
        locations=[l.model_dump() for l in story.locations],
        events=[e.model_dump() for e in story.events],
        themes=[t.model_dump() for t in story.themes],
        relationships=[r.model_dump() for r in story.relationships],
        cultural_context=story.cultural_context.model_dump()
    )


@router.get("/projects/{project_id}/story/acts")
async def get_acts(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get all acts for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    story = project_manager.load_story(project_dir)
    if not story:
        raise HTTPException(status_code=404, detail="Story not analyzed yet")

    return {"acts": [a.model_dump() for a in story.acts]}


@router.get("/projects/{project_id}/story/events")
async def get_events(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get all events for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    story = project_manager.load_story(project_dir)
    if not story:
        raise HTTPException(status_code=404, detail="Story not analyzed yet")

    return {"events": [e.model_dump() for e in story.events]}


@router.get("/projects/{project_id}/story/themes")
async def get_themes(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get all themes for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    story = project_manager.load_story(project_dir)
    if not story:
        raise HTTPException(status_code=404, detail="Story not analyzed yet")

    return {"themes": [t.model_dump() for t in story.themes]}


@router.get("/projects/{project_id}/story/relationships")
async def get_relationships(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get all character relationships for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    story = project_manager.load_story(project_dir)
    if not story:
        raise HTTPException(status_code=404, detail="Story not analyzed yet")

    return {"relationships": [r.model_dump() for r in story.relationships]}


@router.get("/projects/{project_id}/story/cultural-context")
async def get_cultural_context(
    project_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
):
    """Get cultural context for a project."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    story = project_manager.load_story(project_dir)
    if not story:
        raise HTTPException(status_code=404, detail="Story not analyzed yet")

    return story.cultural_context.model_dump()


@router.post("/projects/{project_id}/story/extract-characters")
async def extract_characters(
    project_id: str,
    background_tasks: BackgroundTasks,
    provider: str = "local_python",
    model: str = "llama-3-8b-instruct",
    project_manager: ProjectManager = Depends(get_project_manager),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
):
    """Extract detailed character bibles from story graph."""
    try:
        project_dir = project_manager.get_project_path(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")

    story = project_manager.load_story(project_dir)
    if not story:
        raise HTTPException(status_code=400, detail="Story not analyzed yet")

    # Create character extraction job
    job = Job(
        project_id=project_id,
        type=JobType.CHARACTER_EXTRACTION,
        input={"provider": provider, "model": model},
    )
    await workflow_engine.submit_job(job)

    return {"message": "Character extraction started"}