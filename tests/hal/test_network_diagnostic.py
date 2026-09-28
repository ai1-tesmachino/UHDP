from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.diagnostics.network_diagnostic import (
    NetworkDiagnostic,
)


def test_network_diagnostic():
    diagnostic = NetworkDiagnostic()

    request = DiagnosticRequest(
        diagnostic_type="network",
        device_id="local",
    )

    result = diagnostic.execute(
        request,
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )

    assert (
        "adapter_count"
        in result.details
    )

    assert (
        "adapters"
        in result.details
    )