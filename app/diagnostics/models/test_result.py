from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


class TestStatus:
    PASS = "passed"
    FAIL = "failed"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"
    INCONCLUSIVE = "inconclusive"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    NOT_RUN = "not_run"


class ScanStatus:
    SUCCESS = "success"
    NO_RESULTS = "no_results"
    UNSUPPORTED = "unsupported"
    ERROR = "error"
    NOT_ATTEMPTED = "not_attempted"


class TechnicianDecision:
    WORKING = "working"
    NOT_WORKING = "not_working"
    UNABLE_TO_VERIFY = "unable_to_verify"


@dataclass(slots=True)
class TestResultRecord:
    test_id: str
    test_status: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_run_id: str | None = None
    scan_status: str = ScanStatus.NOT_ATTEMPTED
    detected_devices: list[Any] = field(default_factory=list)
    technician_decision: str | None = None
    technician_notes: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    execution_status: str = "completed"
    recorded_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    retest_history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
