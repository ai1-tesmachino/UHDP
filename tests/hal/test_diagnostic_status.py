from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


def test_status_values():
    assert DiagnosticStatus.PENDING.value == "pending"
    assert DiagnosticStatus.RUNNING.value == "running"
    assert DiagnosticStatus.PASSED.value == "passed"
    assert DiagnosticStatus.FAILED.value == "failed"
    assert DiagnosticStatus.ERROR.value == "error"