from enum import Enum


class DiagnosticStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED = "unsupported"
    INCONCLUSIVE = "inconclusive"
    CANCELLED = "cancelled"