from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class DiagnosticReport:
    report_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    revision_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    supersedes_revision_id: str | None = None
    supersession_reason: str | None = None
    superseded_by: str | None = None
    session_id: str | None = None
    asset_id: str | None = None
    device_id: str = "unknown-device"
    status: str = "pending"
    data: dict[str, Any] = field(
        default_factory=dict
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )