from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    SYSTEM = "system"
    TASK = "task"
    JOB = "job"
    PLUGIN = "plugin"


class RuntimeEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    source: str = "runtime"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Runtime event timestamp must be timezone-aware")
        return value.astimezone(UTC)