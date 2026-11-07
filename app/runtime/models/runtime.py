from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from app.runtime.models.status import JobStatus, RuntimeStatus


class RuntimeJob(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    job_type: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at", "started_at", "completed_at")
    @classmethod
    def normalize_timestamps(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Runtime job timestamps must be timezone-aware")
        return value.astimezone(UTC)


class RuntimeHealth(BaseModel):
    runtime_status: RuntimeStatus
    uptime: float
    active_jobs: int
    queued_jobs: int
    failed_jobs: int
    registered_components: int
    scheduler_status: str
    last_health_check: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("last_health_check")
    @classmethod
    def normalize_health_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Runtime health timestamp must be timezone-aware")
        return value.astimezone(UTC)
