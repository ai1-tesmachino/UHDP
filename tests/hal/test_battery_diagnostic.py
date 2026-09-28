from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.diagnostics.battery_diagnostic import (
    BatteryDiagnostic,
)


def test_battery_diagnostic():
    diagnostic = BatteryDiagnostic()

    result = diagnostic.execute(
        DiagnosticRequest(
            diagnostic_type="battery",
            device_id="local",
        )
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )

    assert (
        "battery_present"
        in result.details
    )