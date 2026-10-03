from enum import Enum


class DiagnosticStatus(
    str,
    Enum,
):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    RUNNING = "running"