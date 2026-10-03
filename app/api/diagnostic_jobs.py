from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.diagnostic_job_service import diagnostic_job_service


router = APIRouter(
    prefix="/diagnostic-jobs",
    tags=["diagnostic-jobs"],
)


class CreateDiagnosticJobRequest(BaseModel):
    test_type: Literal[
        "cpu_stress",
        "memory_stress",
        "gpu_stress",
        "battery_endurance",
    ]
    device_id: str = Field(min_length=1, max_length=200)
    session_id: str | None = Field(default=None, max_length=200)
    parameters: dict[str, Any] = Field(default_factory=dict)
    criteria: dict[str, float] = Field(default_factory=dict)


@router.post("/", status_code=202)
def create_diagnostic_job(
    request: CreateDiagnosticJobRequest,
) -> dict[str, Any]:
    try:
        return diagnostic_job_service.create_job(
            test_type=request.test_type,
            device_id=request.device_id,
            session_id=request.session_id,
            parameters=request.parameters,
            criteria=request.criteria,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/")
def list_diagnostic_jobs(
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    return {"jobs": diagnostic_job_service.list_jobs(limit)}


@router.get("/{job_id}")
def get_diagnostic_job(job_id: str) -> dict[str, Any]:
    job = diagnostic_job_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Diagnostic job not found: {job_id}",
        )
    return job


@router.post("/{job_id}/cancel")
def cancel_diagnostic_job(job_id: str) -> dict[str, Any]:
    job = diagnostic_job_service.cancel_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Diagnostic job not found: {job_id}",
        )
    return job
