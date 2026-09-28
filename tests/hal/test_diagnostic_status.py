from app.hal.diagnostic_status import DiagnosticStatus


def test_diagnostic_status_contains_required_states():
    assert DiagnosticStatus.PENDING.value == "pending"
    assert DiagnosticStatus.RUNNING.value == "running"
    assert DiagnosticStatus.PASSED.value == "passed"
    assert DiagnosticStatus.FAILED.value == "failed"
    assert DiagnosticStatus.ERROR.value == "error"
    assert DiagnosticStatus.SKIPPED.value == "skipped"