from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from datetime import UTC
from datetime import datetime


@dataclass(
    slots=True,
)
class AuditEntry:
    workflow_name: str

    execution_id: str

    message: str

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(
            UTC
        )
    )