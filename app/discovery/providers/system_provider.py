import json
import platform
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


LINUX_DMI_ROOT = Path("/sys/class/dmi/id")
LINUX_EFIVARS_ROOT = Path("/sys/firmware/efi/efivars")
LINUX_TPM_ROOT = Path("/sys/class/tpm")


def _read_dmi_value(name: str) -> str | None:
    try:
        value = (LINUX_DMI_ROOT / name).read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()
    except OSError:
        return None
    return value or None


def _linux_secure_boot() -> dict[str, Any]:
    try:
        variables = sorted(LINUX_EFIVARS_ROOT.glob("SecureBoot-*"))
    except OSError as exc:
        return {"status": "inaccessible", "message": str(exc), "source": "efivarfs"}
    if not variables:
        return {
            "status": "unknown",
            "message": "Secure Boot state is not exposed by EFI variables",
            "source": "efivarfs",
        }
    try:
        value = variables[0].read_bytes()
    except OSError as exc:
        return {"status": "inaccessible", "message": str(exc), "source": "efivarfs"}
    if len(value) < 5 or value[4] not in {0, 1}:
        return {
            "status": "unknown",
            "message": "Secure Boot EFI variable has an invalid value",
            "source": "efivarfs",
        }
    return {
        "status": "enabled" if value[4] else "disabled",
        "enabled": bool(value[4]),
        "source": "efivarfs",
    }


def _linux_tpm_inventory() -> dict[str, Any]:
    try:
        devices = sorted(path.name for path in LINUX_TPM_ROOT.glob("tpm*"))
    except OSError as exc:
        return {
            "devices": [],
            "status": "inaccessible",
            "message": str(exc),
            "source": "sysfs",
        }
    if not LINUX_TPM_ROOT.exists():
        return {
            "devices": [],
            "status": "unsupported",
            "source": "sysfs",
        }
    return {
        "devices": devices,
        "status": "detected" if devices else "not_detected",
        "source": "sysfs",
    }


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
            "collected_at": datetime.now(timezone.utc).isoformat(),
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
                "uuid": _read_dmi_value("product_uuid"),
                "bios_version": _read_dmi_value("bios_version"),
                "bios_vendor": _read_dmi_value("bios_vendor"),
                "bios_date": _read_dmi_value("bios_date"),
                "board_manufacturer": _read_dmi_value("board_vendor"),
                "board_model": _read_dmi_value("board_name"),
                "board_serial_number": _read_dmi_value("board_serial"),
                "secure_boot": _linux_secure_boot(),
                "tpm_inventory": _linux_tpm_inventory(),
                "inventory_source": [
                    "/sys/class/dmi/id",
                    "/etc/os-release",
                    "platform",
                    "/sys/firmware/efi/efivars",
                    "/sys/class/tpm",
                ],
            })
            try:
                properties["linux_distribution"] = platform.freedesktop_os_release()
            except OSError as exc:
                errors["linux_distribution"] = str(exc)
            properties["inventory_status"] = (
                "detected" if properties.get("manufacturer") or properties.get("model")
                else "partial"
            )
            properties["inventory_warnings"] = errors
        else:
            errors["system_identity"] = (
                f"System identity probing is not implemented for {current_platform}"
            )

        properties.setdefault("inventory_warnings", errors)
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
