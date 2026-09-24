from datetime import UTC
from datetime import datetime
from enum import Enum

from pydantic import BaseModel
from pydantic import Field


class EventType(str, Enum):
    SYSTEM = "system"
    TASK = "task"
    JOB = "job"
    PLUGIN = "plugin"


class RuntimeEvent(BaseModel):
    event_type: EventType

    payload: dict = Field(
        default_factory=dict
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            UTC
        )
    )