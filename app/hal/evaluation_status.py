from enum import Enum


class EvaluationStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    UNKNOWN = "unknown"