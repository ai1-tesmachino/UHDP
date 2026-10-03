from dataclasses import dataclass
from dataclasses import field
from typing import Any

from app.diagnostics.models.diagnostic_status import (
    DiagnosticStatus,
)


@dataclass(slots=True)
class DiagnosticResult:
    test_name: str
    status: DiagnosticStatus
    message: str = ""
    details: dict[str, Any] = field(
        default_factory=dict,
    )