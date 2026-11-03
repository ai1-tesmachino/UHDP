import glob
import json
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


LINUX_DRM_ROOT = Path("/sys/class/drm")


def _windows_gpus() -> tuple[list[dict[str, Any]], str | None]:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        return [], "PowerShell unavailable"
    command = """
    Get-CimInstance Win32_VideoController |
    Select-Object Name,AdapterRAM,DriverVersion,VideoProcessor,CurrentHorizontalResolution,CurrentVerticalResolution |
    ConvertTo-Json -Compress
    """
    try:
        response = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [], str(exc)
    if response.returncode != 0:
        return [], response.stderr.strip() or "Windows GPU inventory query failed"
    try:
        devices = json.loads(response.stdout) if response.stdout.strip() else []
    except json.JSONDecodeError as exc:
        return [], f"Windows GPU inventory returned invalid JSON: {exc}"
    if isinstance(devices, dict):
        devices = [devices]
    return devices, None


def _linux_gpus() -> tuple[list[dict[str, Any]], str | None]:
    cards = sorted(glob.glob(str(LINUX_DRM_ROOT / "card[0-9]*")))
    devices = []
    inaccessible = []
    for card in cards:
        card_name = Path(card).name
        if not re.fullmatch(r"card\d+", card_name):
            continue
        device_path = Path(card) / "device"
        try:
            vendor = (device_path / "vendor").read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()
            device_id = (device_path / "device").read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()
        except OSError:
            inaccessible.append(card_name)
            continue

        driver_path = device_path / "driver"
        try:
            driver = driver_path.resolve(strict=True).name
        except OSError:
            driver = None
        try:
            vram = int((device_path / "mem_info_vram_total").read_text().strip())
        except (OSError, ValueError):
            vram = None
        try:
            product_name = (device_path / "product_name").read_text(
                encoding="utf-8",
                errors="replace",
            ).strip()
        except OSError:
            product_name = ""
        temperatures = []
        for hwmon in sorted((device_path / "hwmon").glob("hwmon*")):
            for sensor in sorted(hwmon.glob("temp*_input")):
                try:
                    millidegrees = int(sensor.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ).strip())
                except (OSError, ValueError):
                    continue
                if not -50000 <= millidegrees <= 150000:
                    continue
                label_path = sensor.with_name(
                    sensor.name.removesuffix("_input") + "_label"
                )
                try:
                    label = label_path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ).strip()
                except OSError:
                    label = ""
                temperatures.append({
                    "name": label or sensor.parent.name,
                    "temperature_c": millidegrees / 1000,
                    "source": str(sensor),
                })
        devices.append({
            "name": product_name or card_name,
            "device_path": f"/dev/dri/{card_name}",
            "vendor_id": vendor,
            "device_id": device_id,
            "driver": driver,
            "vram_bytes": vram,
            "temperature_sensors": temperatures,
            "temperature_status": (
                "detected" if temperatures
                else "not_detected" if (device_path / "hwmon").exists()
                else "unsupported"
            ),
            "source": "sysfs DRM/PCI",
        })
    if not LINUX_DRM_ROOT.exists():
        return [], "Linux DRM inventory is unavailable"
    return devices, (
        f"Could not read PCI identifiers for: {', '.join(inaccessible)}"
        if inaccessible
        else None
    )


class GPUProvider(DiscoveryProvider):
    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()
        current_platform = platform.system()
        collected_at = datetime.now(timezone.utc).isoformat()

        if current_platform == "Windows":
            devices, error = _windows_gpus()
        elif current_platform == "Linux":
            devices, error = _linux_gpus()
        else:
            devices, error = [], f"GPU inventory is not implemented for {current_platform}"

        for index, gpu in enumerate(devices):
            if current_platform == "Windows":
                name = gpu.get("Name") or f"GPU {index + 1}"
                properties = {
                    "manufacturer": gpu.get("Name"),
                    "vram_bytes": gpu.get("AdapterRAM"),
                    "driver_version": gpu.get("DriverVersion"),
                    "video_processor": gpu.get("VideoProcessor"),
                    "display_resolution": {
                        "width": gpu.get("CurrentHorizontalResolution"),
                        "height": gpu.get("CurrentVerticalResolution"),
                    },
                }
            else:
                name = gpu["name"]
                properties = gpu
            properties["platform"] = current_platform
            properties["inventory_status"] = "detected"
            properties["collected_at"] = collected_at
            result.add_device(
                Device(
                    device_id=f"gpu:{index}",
                    device_type="gpu",
                    name=name,
                    properties=properties,
                )
            )

        if not devices:
            inventory_status = (
                "unavailable" if error and LINUX_DRM_ROOT.exists()
                else "not_detected" if current_platform == "Linux"
                else "unavailable"
            )
            result.add_device(
                Device(
                    device_id="gpu",
                    device_type="gpu",
                    name="GPU inventory",
                    properties={
                        "detected": False,
                        "platform": current_platform,
                        "inventory_warning": error,
                        "inventory_status": inventory_status,
                        "inventory_source": (
                            "sysfs DRM/PCI" if current_platform == "Linux" else None
                        ),
                        "collected_at": collected_at,
                    },
                )
            )
        return result
