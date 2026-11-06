from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.usb_diagnostic import (
    UsbDiagnostic,
)


def test_usb_diagnostic(monkeypatch, tmp_path):
    import sys
    from app.hal.diagnostics import platform_probes

    usb_root = tmp_path / "sys/bus/usb/devices"
    (usb_root / "1-1").mkdir(parents=True)
    monkeypatch.setattr(platform_probes, "LINUX_ROOT", tmp_path)
    monkeypatch.setattr(platform_probes.platform, "system", lambda: "Linux")
    monkeypatch.setitem(sys.modules, "pyudev", None)

    diagnostic = UsbDiagnostic()

    result = diagnostic.execute(
        DiagnosticRequest(
            diagnostic_type="usb",
            device_id="local",
        )
    )

    assert result.status == DiagnosticStatus.INCONCLUSIVE

    assert (
        "device_count"
        in result.details
    )

    assert (
        "devices"
        in result.details
    )
    assert result.details["device_count"] == 1