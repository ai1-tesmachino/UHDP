from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.dependencies import get_job_manager, get_runtime
from app.runtime.context import RuntimeContext
from app.runtime.managers.job_manager import JobManager
from app.runtime.models import RuntimeJob
from app.runtime.models.runtime import RuntimeHealth
from app.runtime.models.status import JobStatus, RuntimeStatus

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


class RuntimeStatusResponse(BaseModel):
    status: RuntimeStatus


class RuntimeJobResponse(BaseModel):
    job_id: UUID
    job_type: str
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    has_error: bool

    @classmethod
    def from_job(cls, job: RuntimeJob) -> RuntimeJobResponse:
        return cls(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            has_error=job.error is not None,
        )


@router.get("/health", response_model=RuntimeHealth)
def runtime_health(
    runtime: RuntimeContext = Depends(get_runtime),
) -> RuntimeHealth:
    return runtime.get_health()


@router.get("/status", response_model=RuntimeStatusResponse)
def runtime_status(
    runtime: RuntimeContext = Depends(get_runtime),
) -> RuntimeStatusResponse:
    return RuntimeStatusResponse(status=runtime.lifecycle_manager.get_status())


@router.get("/jobs", response_model=list[RuntimeJobResponse])
def list_runtime_jobs(
    limit: int = Query(default=50, ge=1, le=100),
    jobs: JobManager = Depends(get_job_manager),
) -> list[RuntimeJobResponse]:
    return [RuntimeJobResponse.from_job(job) for job in jobs.list_jobs(limit)]


@router.get("/jobs/{job_id}", response_model=RuntimeJobResponse)
def get_runtime_job(
    job_id: UUID,
    jobs: JobManager = Depends(get_job_manager),
) -> RuntimeJobResponse:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Runtime job not found",
        )
    return RuntimeJobResponse.from_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=RuntimeJobResponse)
async def cancel_runtime_job(
    job_id: UUID,
    jobs: JobManager = Depends(get_job_manager),
) -> RuntimeJobResponse:
    job = await jobs.cancel_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Runtime job not found",
        )
    return RuntimeJobResponse.from_job(job)
