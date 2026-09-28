from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.diagnostics.storage_diagnostic import (
    StorageDiagnostic,
)


def test_storage_diagnostic():
    diagnostic = StorageDiagnostic()

    request = DiagnosticRequest(
        diagnostic_type="storage",
        device_id="local",
    )

    result = diagnostic.execute(
        request,
    )

    assert result.status == DiagnosticStatus.PASSED

    assert "current_directory" in result.details
    assert "drives" in result.details

    assert isinstance(
        result.details["drives"],
        list,
    )
  