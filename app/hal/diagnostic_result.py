from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class DiagnosticResult:
    diagnostic_id: str
    diagnostic_type: str
    device_id: str
    status: Any

    message: str = ""

    details: dict[str, Any] = field(
        default_factory=dict
    )

    evaluation: Any | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )