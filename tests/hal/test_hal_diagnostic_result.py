from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


def test_result_creation():
    result = DiagnosticResult(
        diagnostic_id="diag-1",
        diagnostic_type="cpu",
        device_id="device-1",
        status=DiagnosticStatus.PASSED,
    )

    assert result.diagnostic_id == "diag-1"
    assert result.diagnostic_type == "cpu"
    assert result.device_id == "device-1"
    assert result.status == DiagnosticStatus.PASSED
    assert result.details == {}
    assert result.created_at is not None