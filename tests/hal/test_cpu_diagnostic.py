from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.diagnostics.cpu_diagnostic import (
    CpuDiagnostic,
)


def test_cpu_diagnostic():
    diagnostic = CpuDiagnostic()

    request = DiagnosticRequest(
        diagnostic_type="cpu",
        device_id="local",
    )

    result = diagnostic.execute(
        request,
    )

    assert result.diagnostic_id == request.diagnostic_id
    assert result.status == DiagnosticStatus.PASSED
    assert "architecture" in result.details
    assert "logical_cores" in result.details
    assert "physical_cores" in result.details
    assert "cpu_usage_percent" in result.details