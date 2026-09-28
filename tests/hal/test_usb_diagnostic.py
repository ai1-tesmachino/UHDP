from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.hal.diagnostics.usb_diagnostic import (
    UsbDiagnostic,
)


def test_usb_diagnostic():
    diagnostic = UsbDiagnostic()

    result = diagnostic.execute(
        DiagnosticRequest(
            diagnostic_type="usb",
            device_id="local",
        )
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )

    assert (
        "device_count"
        in result.details
    )

    assert (
        "devices"
        in result.details
    )