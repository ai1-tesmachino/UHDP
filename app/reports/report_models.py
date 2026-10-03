from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any


@dataclass
class DiagnosticReport:

    report_id: str
    session_id: str
    device_id: str

    started_at: datetime | None = None
    completed_at: datetime | None = None

    overall_status: str = "UNKNOWN"

    total_diagnostics: int = 0
    passed_diagnostics: int = 0
    failed_diagnostics: int = 0

    results: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportSummary:

    report_id: str
    session_id: str
    device_id: str

    overall_status: str

    total_diagnostics: int
    passed_diagnostics: int
    failed_diagnostics: int

    completed_at: datetime | None = None