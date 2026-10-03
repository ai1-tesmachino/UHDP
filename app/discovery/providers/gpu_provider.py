import glob
import json
import platform
import shutil
import subprocess
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
    for card in cards:
        device_path = Path(card) / "device"
        try:
            vendor = (device_path / "vendor").read_text().strip()
            device_id = (device_path / "device").read_text().strip()
        except OSError:
            continue

        driver_path = device_path / "driver"
        try:
            driver = driver_path.resolve().name
        except OSError:
            driver = None
        try:
            vram = int((device_path / "mem_info_vram_total").read_text().strip())
        except (OSError, ValueError):
            vram = None
        devices.append({
            "name": card.rsplit("/", 1)[-1],
            "vendor_id": vendor,
            "device_id": device_id,
            "driver": driver,
            "vram_bytes": vram,
        })
    if not LINUX_DRM_ROOT.exists():
        return [], "Linux DRM inventory is unavailable"
    return devices, None


class GPUProvider(DiscoveryProvider):
    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()
        current_platform = platform.system()

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
            result.add_device(
                Device(
                    device_id=f"gpu:{index}",
                    device_type="gpu",
                    name=name,
                    properties=properties,
                )
            )

        if not devices:
            result.add_device(
                Device(
                    device_id="gpu",
                    device_type="gpu",
                    name="GPU inventory",
                    properties={
                        "detected": False,
                        "platform": current_platform,
                        "inventory_warning": error,
                    },
                )
            )
        return result
