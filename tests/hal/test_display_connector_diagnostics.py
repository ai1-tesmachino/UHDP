from unittest.mock import patch

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.hdmi_diagnostic import HdmiDiagnostic
from app.hal.diagnostics.vga_diagnostic import VgaDiagnostic


def test_hdmi_diagnostic_queries_connection_parameters():
    with patch(
        "app.hal.diagnostics.hdmi_diagnostic.run_powershell",
        return_value={
            "InstanceName": "DISPLAY\\HDMI",
            "Active": True,
            "VideoOutputTechnology": 10,
        },
    ) as run_powershell:
        result = HdmiDiagnostic().execute(
            DiagnosticRequest(
                diagnostic_type="hdmi",
                device_id="system",
            )
        )

    command = run_powershell.call_args.args[0]
    assert "Get-CimInstance `" in command
    assert result.status == DiagnosticStatus.PASSED
    assert result.details["hdmi_present"] is True
    assert result.details["hdmi_connection_count"] == 1


def test_vga_diagnostic_queries_connection_parameters():
    with patch(
        "app.hal.diagnostics.vga_diagnostic.run_powershell",
        return_value={
            "InstanceName": "DISPLAY\\VGA",
            "Active": True,
            "VideoOutputTechnology": 5,
        },
    ) as run_powershell:
        result = VgaDiagnostic().execute(
            DiagnosticRequest(
                diagnostic_type="vga",
                device_id="system",
            )
        )

    command = run_powershell.call_args.args[0]
    assert "Get-CimInstance `" in command
    assert result.status == DiagnosticStatus.PASSED
    assert result.details["vga_present"] is True
    assert result.details["vga_connection_count"] == 1
