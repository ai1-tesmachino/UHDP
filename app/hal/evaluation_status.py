from enum import Enum


class EvaluationStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"
    NOT_APPLICABLE = "not_applicable"
    INCONCLUSIVE = "inconclusive"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"