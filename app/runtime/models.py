from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeStatus(str, Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


class EventType(str, Enum):
    SYSTEM = "system"
    SESSION = "session"
    JOB = "job"
    DEVICE = "device"


class RuntimeEvent(BaseModel):
    id: str
    event_type: EventType
    source: str
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeJob(BaseModel):
    id: str
    name: str
    created_at: datetime
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)