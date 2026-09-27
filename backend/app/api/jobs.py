"""
Jobs API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.models.job import Job, JobStatus, JobType, JobStep
from app.workflow.engine import WorkflowEngine
from app.services.project_manager import ProjectManager


router = APIRouter()


def get_workflow_engine() -> WorkflowEngine:
    from app.main import app
    return app.state.workflow_engine


def get_project_manager() -> ProjectManager:
    from app.main import app
    return app.state.project_manager


class JobResponse(BaseModel):
    job_id: str
    project_id: UUID
    type: JobType
    status: JobStatus
    progress: int
    current_step: str
    total_steps: int
    steps: List[JobStep]
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int
    cancel_requested: bool


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int


class JobCancelRequest(BaseModel):
    reason: str = "User requested cancellation"


class JobRetryRequest(BaseModel):
    pass


@router.get("/projects/{project_id}/jobs", response_model=JobListResponse)
async def list_jobs(
    project_id: UUID,
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    project_manager: ProjectManager = Depends(get_project_manager),
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> JobListResponse:
    """List all jobs for a project."""
    try:
        project_manager.load_project(str(project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    jobs = workflow_engine.list_jobs(project_id)
    
    if status:
        jobs = [j for j in jobs if j.status == status]
    if job_type:
        jobs = [j for j in jobs if j.type == job_type]
    
    total = len(jobs)
    jobs = jobs[offset:offset + limit]
    
    return JobListResponse(
        jobs=[
            JobResponse(
                job_id=j.job_id,
                project_id=j.project_id,
                type=j.type,
                status=j.status,
                progress=j.progress,
                current_step=j.current_step,
                total_steps=j.total_steps,
                steps=j.steps,
                error=j.error,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
                retry_count=j.retry_count,
                cancel_requested=j.cancel_requested,
            )
            for j in jobs
        ],
        total=total,
    )


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
        total_steps=job.total_steps,
        steps=job.steps,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        retry_count=job.retry_count,
        cancel_requested=job.cancel_requested,
    )


@router.post("/projects/{project_id}/jobs/{job_id}/cancel")
async def cancel_job(
    project_id: UUID,
    job_id: str,
    request: JobCancelRequest,
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
    
    return {"message": "Job cancelled", "job_id": job_id, "reason": request.reason}


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


@router.get("/projects/{project_id}/jobs/{job_id}/logs")
async def get_job_logs(
    project_id: UUID,
    job_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, Any]:
    """Get job logs."""
    try:
        project_manager.load_project(str(project_id))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Project not found")
    
    job = project_manager.load_job(
        project_manager.get_project_path(str(project_id)), job_id
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return job steps as logs
    return {
        "job_id": job_id,
        "steps": [step.model_dump() for step in job.steps],
        "current_step": job.current_step,
        "progress": job.progress,
        "status": job.status.value,
    }