from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class DiagnosticResult:
    diagnostic_id: str
    diagnostic_type: str
    device_id: str
    status: Any
    run_id: str | None = field(default_factory=lambda: str(uuid4()))

    session_id: str | None = None
    asset_id: str | None = None
    component_id: str | None = None
    message: str = ""

    details: dict[str, Any] = field(
        default_factory=dict
    )

    evaluation: Any | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
