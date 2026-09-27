"""
Projects API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.models.project import (
    ProjectManifest, ProjectCreate, ProjectUpdate, ProjectSummary,
    ProjectStatus, ProviderConfigMap, ModelConfiguration, WorkflowState
)
from app.models.job import Job, JobType, JobStatus
from app.services.project_manager import ProjectManager
from app.workflow.engine import WorkflowEngine
from app.core.config import get_settings


router = APIRouter()


# Dependency injection helpers
def get_project_manager() -> ProjectManager:
    from app.main import app
    return app.state.project_manager


def get_workflow_engine() -> WorkflowEngine:
    from app.main import app
    return app.state.workflow_engine


class ProjectListResponse(BaseModel):
    projects: List[ProjectSummary]
    total: int


class JobCreateRequest(BaseModel):
    type: JobType
    input: Dict[str, Any] = {}
    provider: str = ""
    priority: int = 0
    depends_on: List[str] = []


class JobResponse(BaseModel):
    job_id: str
    project_id: UUID
    type: JobType
    status: JobStatus
    progress: int
    current_step: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@router.post("/projects", response_model=ProjectManifest, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> ProjectManifest:
    """Create a new project."""
    try:
        project = project_manager.create_project(project_data)
        return project
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    project_manager: ProjectManager = Depends(get_project_manager),
    status: Optional[ProjectStatus] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ProjectListResponse:
    """List all projects."""
    projects = project_manager.list_projects()
    
    if status:
        projects = [p for p in projects if p.status == status]
    
    total = len(projects)
    projects = projects[offset:offset + limit]
    
    return ProjectListResponse(projects=projects, total=total)


@router.get("/projects/{project_id}", response_model=ProjectManifest)
async def get_project(
    project_id: UUID,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> ProjectManifest:
    """Get project by ID."""
    try:
        project = project_manager.load_project(str(project_id))
        return project
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/projects/{project_id}", response_model=ProjectManifest)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> ProjectManifest:
    """Update project."""
    try:
        project = project_manager.load_project(str(project_id))
        
        # Apply updates
        update_data = project_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)
        
        project.updated_at = datetime.utcnow()
        
        project_dir = project_manager.get_project_path(str(project_id))
        project_manager.save_project(project_dir, project)
        
        return project
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> None:
    """Delete a project."""
    success = project_manager.delete_project(str(project_id))
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/projects/{project_id}/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    project_id: UUID,
    job_request: JobCreateRequest,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> JobResponse:
    """Create and submit a new job."""
    # Verify project exists
    try:
        project_manager.load_project(str(project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create job
    job = Job(
        project_id=project_id,
        type=job_request.type,
        input=job_request.input,
        provider=job_request.provider,
        priority=job_request.priority,
        depends_on=job_request.depends_on,
    )
    
    # Submit to workflow engine
    await workflow_engine.submit_job(job)
    
    return JobResponse(
        job_id=job.job_id,
        project_id=job.project_id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get("/projects/{project_id}/jobs", response_model=List[JobResponse])
async def list_jobs(
    project_id: UUID,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    project_manager: ProjectManager = Depends(get_project_manager),
    status: Optional[JobStatus] = None,
) -> List[JobResponse]:
    """List all jobs for a project."""
    try:
        project_manager.load_project(str(project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    jobs = workflow_engine.list_jobs(project_id)
    
    if status:
        jobs = [j for j in jobs if j.status == status]
    
    return [
        JobResponse(
            job_id=j.job_id,
            project_id=j.project_id,
            type=j.type,
            status=j.status,
            progress=j.progress,
            current_step=j.current_step,
            created_at=j.created_at,
            started_at=j.started_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]


@router.get("/projects/{project_id}/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    project_id: UUID,
    job_id: str,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> JobResponse:
    """Get job status."""
    try:
        project_manager.load_project(str(project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    job = workflow_engine.get_job_status(project_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(
        job_id=job.job_id,
        project_id=job.project_id,
        type=job.type,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post("/projects/{project_id}/jobs/{job_id}/cancel")
async def cancel_job(
    project_id: UUID,
    job_id: str,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, str]:
    """Cancel a job."""
    try:
        project_manager.load_project(str(project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    success = await workflow_engine.cancel_job(project_id, job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    
    return {"message": "Job cancelled", "job_id": job_id}


@router.post("/projects/{project_id}/jobs/{job_id}/retry")
async def retry_job(
    project_id: UUID,
    job_id: str,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, str]:
    """Retry a failed job."""
    try:
        project_manager.load_project(str(project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    success = await workflow_engine.retry_job(project_id, job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be retried")
    
    return {"message": "Job queued for retry", "job_id": job_id}


@router.post("/projects/{project_id}/recover")
async def recover_jobs(
    project_id: UUID,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, Any]:
    """Recover incomplete jobs from previous session."""
    try:
        project_manager.load_project(str(project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    recovered = await workflow_engine.recover_incomplete_jobs(project_id)
    
    return {
        "message": f"Recovered {len(recovered)} jobs",
        "recovered_job_ids": recovered,
    }


@router.get("/projects/{project_id}/queue/status")
async def get_queue_status(
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
) -> Dict[str, Any]:
    """Get workflow queue status."""
    return workflow_engine.get_queue_status()