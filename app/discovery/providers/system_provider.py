import json
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


LINUX_DMI_ROOT = Path("/sys/class/dmi/id")


def _read_dmi_value(name: str) -> str | None:
    try:
        value = (LINUX_DMI_ROOT / name).read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()
    except OSError:
        return None
    return value or None


def _windows_identity() -> tuple[dict[str, Any], str | None]:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        return {}, "PowerShell unavailable"

    command = """
    $system = Get-CimInstance Win32_ComputerSystem
    $bios = Get-CimInstance Win32_BIOS
    [PSCustomObject]@{
        Manufacturer = $system.Manufacturer
        Model = $system.Model
        SerialNumber = $bios.SerialNumber
        BiosVersion = ($bios.SMBIOSBIOSVersion -join ', ')
    } | ConvertTo-Json -Compress
    """
    try:
        response = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {}, str(exc)

    if response.returncode != 0:
        return {}, response.stderr.strip() or "Windows CIM query failed"
    try:
        payload = json.loads(response.stdout)
    except json.JSONDecodeError as exc:
        return {}, f"Windows CIM returned invalid JSON: {exc}"
    return (payload if isinstance(payload, dict) else {}), None


class SystemProvider(DiscoveryProvider):
    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()
        current_platform = platform.system()
        properties: dict[str, Any] = {
            "hostname": socket.gethostname(),
            "os_name": current_platform,
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "platform": platform.platform(),
        }

        errors = {}
        if current_platform == "Windows":
            identity, error = _windows_identity()
            if error:
                errors["system_identity"] = error
            properties.update({
                "manufacturer": identity.get("Manufacturer"),
                "model": identity.get("Model"),
                "serial_number": identity.get("SerialNumber"),
                "bios_version": identity.get("BiosVersion"),
            })
        elif current_platform == "Linux":
            properties.update({
                "manufacturer": _read_dmi_value("sys_vendor"),
                "model": _read_dmi_value("product_name"),
                "serial_number": _read_dmi_value("product_serial"),
                "bios_version": _read_dmi_value("bios_version"),
                "board_manufacturer": _read_dmi_value("board_vendor"),
                "board_model": _read_dmi_value("board_name"),
            })
            try:
                properties["linux_distribution"] = platform.freedesktop_os_release()
            except OSError as exc:
                errors["linux_distribution"] = str(exc)
        else:
            errors["system_identity"] = (
                f"System identity probing is not implemented for {current_platform}"
            )

        properties["inventory_warnings"] = errors
        name = " ".join(
            part
            for part in (
                properties.get("manufacturer"),
                properties.get("model"),
            )
            if isinstance(part, str) and part.strip()
        ) or socket.gethostname()

        result.add_device(
            Device(
                device_id="system",
                device_type="system",
                name=name,
                properties=properties,
            )
        )
        return result
