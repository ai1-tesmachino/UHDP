import platform
from pathlib import Path

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus

LINUX_ROOT = Path("/")


def _result(
    request: DiagnosticRequest,
    status: DiagnosticStatus,
    message: str,
    details: dict,
) -> DiagnosticResult:
    return DiagnosticResult(
        diagnostic_id=request.diagnostic_id,
        diagnostic_type=request.diagnostic_type,
        device_id=request.device_id,
        status=status,
        message=message,
        details={"platform": platform.system(), **details},
    )


def unsupported_result(
    request: DiagnosticRequest,
    message: str,
) -> DiagnosticResult:
    return _result(
        request,
        DiagnosticStatus.UNSUPPORTED,
        message,
        {},
    )


def linux_inventory_probe(
    request: DiagnosticRequest,
    kind: str,
) -> DiagnosticResult | None:
    current_platform = platform.system()
    if current_platform == "Windows":
        return None
    if current_platform != "Linux":
        return unsupported_result(
            request,
            f"{kind} inventory probing is not implemented for {current_platform}",
        )

    root = LINUX_ROOT
    try:
        if kind == "wifi":
            net_root = root / "sys/class/net"
            adapters = [
                path.name
                for path in net_root.iterdir()
                if (path / "wireless").exists()
            ]
            present = bool(adapters)
            return _result(
                request,
                DiagnosticStatus.PASSED if present else DiagnosticStatus.NOT_APPLICABLE,
                "Wi-Fi adapter inventory completed; connection is operator-confirmed",
                {"wifi_adapter_present": present, "adapters": adapters, "adapter_count": len(adapters)},
            )

        if kind == "bluetooth":
            bluetooth_root = root / "sys/class/bluetooth"
            devices = (
                [path.name for path in bluetooth_root.iterdir()]
                if bluetooth_root.exists()
                else []
            )
            present = bool(devices)
            return _result(
                request,
                DiagnosticStatus.PASSED if present else DiagnosticStatus.NOT_APPLICABLE,
                "Bluetooth controller inventory completed; pairing is operator-confirmed",
                {"bluetooth_present": present, "controllers": devices, "controller_count": len(devices)},
            )

        if kind == "webcam":
            devices = [path.name for path in (root / "dev").glob("video*")]
            present = bool(devices)
            return _result(
                request,
                DiagnosticStatus.PASSED if present else DiagnosticStatus.NOT_APPLICABLE,
                "Webcam device-node inventory completed; image quality is operator-confirmed",
                {"webcam_present": present, "cameras": devices, "camera_count": len(devices)},
            )

        if kind == "keyboard":
            keyboard_root = root / "dev/input/by-path"
            devices = [
                path.name
                for path in keyboard_root.glob("*-event-kbd")
            ] if keyboard_root.exists() else []
            present = bool(devices)
            return _result(
                request,
                DiagnosticStatus.PASSED if present else DiagnosticStatus.NOT_APPLICABLE,
                "Keyboard device-node inventory completed; key input is operator-confirmed",
                {"keyboard_present": present, "keyboards": devices, "keyboard_count": len(devices)},
            )

        if kind == "speaker":
            cards = root / "proc/asound/cards"
            if not cards.exists():
                return unsupported_result(
                    request,
                    "ALSA audio inventory is unavailable; confirm speaker output manually",
                )
            lines = [
                line.strip()
                for line in cards.read_text(encoding="utf-8", errors="replace").splitlines()
                if line.strip() and not line.lstrip().startswith("--")
            ]
            present = bool(lines)
            return _result(
                request,
                DiagnosticStatus.PASSED if present else DiagnosticStatus.NOT_APPLICABLE,
                "Audio device inventory completed; audible output is operator-confirmed",
                {"audio_devices": lines, "audio_device_count": len(lines)},
            )

        if kind in {"display", "hdmi", "vga"}:
            drm_root = root / "sys/class/drm"
            if not drm_root.exists():
                return unsupported_result(
                    request,
                    "DRM connector inventory is unavailable on this Linux system",
                )
            connectors = []
            for path in drm_root.glob("card*-*"):
                if kind == "hdmi" and "HDMI" not in path.name.upper():
                    continue
                if kind == "vga" and "VGA" not in path.name.upper():
                    continue
                status_file = path / "status"
                if status_file.exists():
                    connectors.append({
                        "name": path.name,
                        "status": status_file.read_text(encoding="utf-8", errors="replace").strip(),
                    })
            connected = [item for item in connectors if item["status"] == "connected"]
            return _result(
                request,
                DiagnosticStatus.PASSED if connected else DiagnosticStatus.NOT_APPLICABLE,
                f"{kind.upper()} display connector inventory completed",
                {"connector_count": len(connectors), "connected_count": len(connected), "connectors": connectors},
            )

        if kind == "usb":
            usb_root = root / "sys/bus/usb/devices"
            if not usb_root.exists():
                return unsupported_result(
                    request,
                    "Linux USB sysfs inventory is unavailable",
                )
            devices = [
                path.name
                for path in usb_root.iterdir()
                if ":" not in path.name
            ]
            present = bool(devices)
            return _result(
                request,
                DiagnosticStatus.PASSED if present else DiagnosticStatus.NOT_APPLICABLE,
                "USB device inventory completed",
                {"device_count": len(devices), "devices": devices},
            )

        if kind == "usb_c":
            thunderbolt_root = root / "sys/bus/thunderbolt/devices"
            if thunderbolt_root.exists() and any(thunderbolt_root.iterdir()):
                devices = [path.name for path in thunderbolt_root.iterdir()]
                return _result(
                    request,
                    DiagnosticStatus.PASSED,
                    "Thunderbolt device inventory completed; USB-C port capability cannot be inferred from connected devices",
                    {"thunderbolt_devices": devices, "usb_c_port_capability": "unknown"},
                )
            return unsupported_result(
                request,
                "Linux sysfs cannot reliably identify unconnected USB-C ports; inspect the port and classify it manually",
            )

    except OSError as exc:
        return unsupported_result(
            request,
            f"{kind} inventory is unavailable: {exc}",
        )

    return unsupported_result(
        request,
        f"{kind} inventory probing is not implemented for {current_platform}",
    )
LINUX_ROOT = Path("/")
