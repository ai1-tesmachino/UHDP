from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.diagnostics.memory_diagnostic import (
    MemoryDiagnostic,
)


def test_memory_diagnostic():
    diagnostic = MemoryDiagnostic()

    request = DiagnosticRequest(
        diagnostic_type="memory",
        device_id="local",
    )

    result = diagnostic.execute(
        request,
    )

    assert result.status == DiagnosticStatus.PASSED
    assert result.details["total_ram_mb"] > 0
    assert result.details["available_ram_mb"] >= 0
    assert result.details["used_ram_mb"] >= 0
    assert "usage_percent" in result.details