from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from typing import Any

from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


@dataclass(slots=True)
class DiagnosticResult:
    diagnostic_id: str
    diagnostic_type: str
    device_id: str
    status: DiagnosticStatus
    message: str = ""
    details: dict[str, Any] = field(
        default_factory=dict
    )
    created_at: datetime = field(
    default_factory=lambda: datetime.now(UTC)
)