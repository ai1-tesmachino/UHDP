from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.diagnostics.system_diagnostic import (
    SystemDiagnostic,
)


def test_system_diagnostic():
    diagnostic = SystemDiagnostic()

    result = diagnostic.execute(
        DiagnosticRequest(
            diagnostic_type="system",
            device_id="local",
        )
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )

    assert (
        "hostname"
        in result.details
    )

    assert (
        "operating_system"
        in result.details
    )

    assert (
        "architecture"
        in result.details
    )