from unittest.mock import patch

import pytest

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_status import DiagnosticStatus

from app.hal.diagnostics.battery_diagnostic import BatteryDiagnostic
from app.hal.diagnostics.bluetooth_diagnostic import BluetoothDiagnostic
from app.hal.diagnostics.display_diagnostic import DisplayDiagnostic
from app.hal.diagnostics.hdmi_diagnostic import HdmiDiagnostic
from app.hal.diagnostics.keyboard_diagnostic import KeyboardDiagnostic
from app.hal.diagnostics.speaker_diagnostic import SpeakerDiagnostic
from app.hal.diagnostics.usb_c_diagnostic import UsbCDiagnostic
from app.hal.diagnostics.usb_diagnostic import UsbDiagnostic
from app.hal.diagnostics.vga_diagnostic import VgaDiagnostic
from app.hal.diagnostics.webcam_diagnostic import WebcamDiagnostic
from app.hal.diagnostics.wifi_diagnostic import WifiDiagnostic


@pytest.mark.parametrize(
    "diagnostic_class,module_name,diagnostic_type,payload,expected_key",
    [
        (
            DisplayDiagnostic,
            "display_diagnostic",
            "display",
            {
                "Name": "Generic Monitor",
                "PNPDeviceID": "DISPLAY001",
                "Status": "OK",
            },
            "display_present",
        ),
        (
            WebcamDiagnostic,
            "webcam_diagnostic",
            "webcam",
            {
                "FriendlyName": "USB Webcam",
                "Status": "OK",
                "Class": "Camera",
                "InstanceId": "CAM001",
            },
            "webcam_present",
        ),
        (
            KeyboardDiagnostic,
            "keyboard_diagnostic",
            "keyboard",
            {
                "FriendlyName": "Standard Keyboard",
                "Status": "OK",
                "Class": "Keyboard",
                "InstanceId": "KEY001",
            },
            "keyboard_present",
        ),
        (
            SpeakerDiagnostic,
            "speaker_diagnostic",
            "speaker",
            {
                "Name": "Speakers",
                "Status": "OK",
            },
            "speaker_present",
        ),
        (
            UsbCDiagnostic,
            "usb_c_diagnostic",
            "usb_c",
            {
                "FriendlyName": "USB Type-C Controller",
                "Status": "OK",
                "Class": "USB",
                "InstanceId": "USBC001",
            },
            "usb_c_device_present",
        ),
        (
            HdmiDiagnostic,
            "hdmi_diagnostic",
            "hdmi",
            {
                "InstanceName": "HDMI001",
                "Active": True,
                "VideoOutputTechnology": 10,
            },
            "hdmi_present",
        ),
        (
            VgaDiagnostic,
            "vga_diagnostic",
            "vga",
            {
                "InstanceName": "VGA001",
                "Active": True,
                "VideoOutputTechnology": 5,
            },
            "vga_present",
        ),
        (
            WifiDiagnostic,
            "wifi_diagnostic",
            "wifi",
            {
                "Name": "Wi-Fi",
                "InterfaceDescription": "Wireless Adapter",
                "Status": "Up",
                "LinkSpeed": "433 Mbps",
                "MacAddress": "00-11-22-33-44-55",
            },
            "wifi_adapter_present",
        ),
        (
            BluetoothDiagnostic,
            "bluetooth_diagnostic",
            "bluetooth",
            {
                "FriendlyName": "Bluetooth Adapter",
                "Status": "OK",
                "Class": "Bluetooth",
                "InstanceId": "BT001",
            },
            "bluetooth_present",
        ),
    ],
)
def test_basic_hardware_diagnostic_passes(
    diagnostic_class,
    module_name,
    diagnostic_type,
    payload,
    expected_key,
):
    with patch(
        f"app.hal.diagnostics.{module_name}.run_powershell",
        return_value=payload,
    ):
        diagnostic = diagnostic_class()

        result = diagnostic.execute(
            DiagnosticRequest(
                diagnostic_type=diagnostic_type,
                device_id="test-device",
            )
        )

    assert result.status == DiagnosticStatus.PASSED
    assert result.diagnostic_type == diagnostic_type
    assert result.device_id == "test-device"
    assert result.details[expected_key] is True


def test_battery_diagnostic_passes():
    battery = type(
        "Battery",
        (),
        {
            "percent": 80,
            "secsleft": 3600,
            "power_plugged": False,
        },
    )()

    with patch(
        "app.hal.diagnostics.battery_diagnostic.psutil.sensors_battery",
        return_value=battery,
    ):
        result = BatteryDiagnostic().execute(
            DiagnosticRequest(
                diagnostic_type="battery",
                device_id="test-device",
            )
        )

    assert result.status == DiagnosticStatus.PASSED
    assert result.diagnostic_type == "battery"
    assert result.device_id == "test-device"
    assert result.details["battery_present"] is True

def test_usb_diagnostic_passes():
    with patch(
        "app.hal.diagnostics.usb_diagnostic.run_powershell",
        return_value=[{"FriendlyName": "USB Root Hub", "Status": "OK"}],
    ):

        result = UsbDiagnostic().execute(
            DiagnosticRequest(
                diagnostic_type="usb",
                device_id="test-device",
            )
        )

    assert result.status == DiagnosticStatus.PASSED
    assert result.diagnostic_type == "usb"
    assert result.device_id == "test-device"
    assert result.details["device_count"] == 1
    assert len(result.details["devices"]) == 1


def test_usb_diagnostic_handles_error():
    with patch(
        "app.hal.diagnostics.usb_diagnostic.run_powershell",
        side_effect=RuntimeError(
            "usb query failed"
        ),
    ):
        result = UsbDiagnostic().execute(
            DiagnosticRequest(
                diagnostic_type="usb",
                device_id="test-device",
            )
        )

    assert result.status == DiagnosticStatus.ERROR
    assert result.diagnostic_type == "usb"
    assert result.device_id == "test-device"
    assert result.message == "usb query failed"


@pytest.mark.parametrize(
    "diagnostic_class,module_name,diagnostic_type",
    [
        (
            DisplayDiagnostic,
            "display_diagnostic",
            "display",
        ),
        (
            WebcamDiagnostic,
            "webcam_diagnostic",
            "webcam",
        ),
        (
            KeyboardDiagnostic,
            "keyboard_diagnostic",
            "keyboard",
        ),
        (
            SpeakerDiagnostic,
            "speaker_diagnostic",
            "speaker",
        ),
        (
            UsbCDiagnostic,
            "usb_c_diagnostic",
            "usb_c",
        ),
        (
            HdmiDiagnostic,
            "hdmi_diagnostic",
            "hdmi",
        ),
        (
            VgaDiagnostic,
            "vga_diagnostic",
            "vga",
        ),
        (
            WifiDiagnostic,
            "wifi_diagnostic",
            "wifi",
        ),
        (
            BluetoothDiagnostic,
            "bluetooth_diagnostic",
            "bluetooth",
        ),
    ],
)



def test_basic_hardware_diagnostic_handles_error(
    diagnostic_class,
    module_name,
    diagnostic_type,
):
    with patch(
        f"app.hal.diagnostics.{module_name}.run_powershell",
        side_effect=RuntimeError(
            "hardware query failed"
        ),
    ):
        result = diagnostic_class().execute(
            DiagnosticRequest(
                diagnostic_type=diagnostic_type,
                device_id="test-device",
            )
        )

    assert result.status == DiagnosticStatus.ERROR
    assert result.diagnostic_type == diagnostic_type
    assert result.device_id == "test-device"
    assert result.message == "hardware query failed"


def test_battery_diagnostic_handles_error():
    with patch(
        "app.hal.diagnostics.battery_diagnostic.psutil.sensors_battery",
        side_effect=RuntimeError(
            "battery query failed"
        ),
    ):
        result = BatteryDiagnostic().execute(
            DiagnosticRequest(
                diagnostic_type="battery",
                device_id="test-device",
            )
        )

    assert result.status == DiagnosticStatus.ERROR
    assert result.diagnostic_type == "battery"
    assert result.device_id == "test-device"
    assert result.message == "battery query failed"

