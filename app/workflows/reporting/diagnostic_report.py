from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class DiagnosticReport:
    report_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    device_id: str = "unknown-device"
    status: str = "pending"
    data: dict[str, Any] = field(
        default_factory=dict
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )