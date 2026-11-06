import psutil

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
        == DiagnosticStatus.INCONCLUSIVE
    )

    assert (
        "adapter_count"
        in result.details
    )

    assert (
        "adapters"
        in result.details
    )
    assert result.details["connectivity_verified"] is False
    assert "connectivity was not tested" in result.message


def test_network_diagnostic_classifies_permission_errors(monkeypatch):
    monkeypatch.setattr(
        psutil,
        "net_if_addrs",
        lambda: (_ for _ in ()).throw(PermissionError("access denied")),
    )
    result = NetworkDiagnostic().execute(
        DiagnosticRequest(
            diagnostic_type="network",
            device_id="local",
        )
    )

    assert result.status == DiagnosticStatus.INCONCLUSIVE
    assert result.details["error_category"] == "permission_denied"
    assert result.details["scan_status"] == "error"
    assert "Permission denied" in result.message