import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device

LINUX_DRM_ROOT = Path("/sys/class/drm")


class DisplayProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        resolution = "Unknown"
        display_modes = []
        connectors = []
        refresh_rate_hz = None
        manufacturer = None
        model = None
        display_name = None

        if platform.system() == "Linux":
            for connector in sorted(LINUX_DRM_ROOT.glob("card*-*")):
                try:
                    status = (connector / "status").read_text(
                        encoding="utf-8",
                        errors="replace",
                    ).strip()
                except OSError:
                    continue
                modes_path = connector / "modes"
                try:
                    modes = [
                        line.strip()
                        for line in modes_path.read_text(
                            encoding="utf-8",
                            errors="replace",
                        ).splitlines()
                        if line.strip()
                    ]
                except OSError:
                    modes = []
                connector_info = {
                    "name": connector.name,
                    "status": status,
                    "modes": modes,
                }
                edid = _read_edid(connector / "edid")
                if edid is not None:
                    connector_info["edid"] = edid
                    if status == "connected" and manufacturer is None:
                        manufacturer = edid.get("manufacturer")
                        model = edid.get("model")
                        display_name = edid.get("display_name")
                connectors.append(connector_info)
                if status == "connected":
                    display_modes.extend(modes)
            xrandr = shutil.which("xrandr")
            if xrandr:
                try:
                    current_display = subprocess.run(
                        [xrandr, "--current"],
                        capture_output=True,
                        text=True,
                        timeout=4,
                        check=False,
                    )
                    if current_display.returncode == 0:
                        for line in current_display.stdout.splitlines():
                            match = re.match(
                                r"^\s+(\d+x\d+)\s+(.+)$",
                                line,
                            )
                            if not match:
                                continue
                            active = next(
                                (
                                    token
                                    for token in match.group(2).split()
                                    if "*" in token
                                ),
                                None,
                            )
                            if active:
                                resolution = match.group(1)
                                refresh_rate_hz = float(
                                    active.replace("*", "").replace("+", "")
                                )
                                break
                except (OSError, subprocess.SubprocessError, ValueError):
                    pass
        elif platform.system() == "Windows":
            try:
                output = subprocess.check_output(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        "(Get-CimInstance Win32_VideoController | Select-Object -First 1 CurrentHorizontalResolution,CurrentVerticalResolution | ConvertTo-Json -Compress)",
                    ],
                    text=True,
                    timeout=10,
                )
                import json

                data = json.loads(output)
                width = data.get("CurrentHorizontalResolution")
                height = data.get("CurrentVerticalResolution")
                if width and height:
                    resolution = f"{width}x{height}"
            except (OSError, subprocess.SubprocessError, ValueError):
                pass

        device = Device(
            device_id="display",
            device_type="display",
            name="Display",
            properties={
                "resolution": resolution,
                "supported_modes": list(dict.fromkeys(display_modes)),
                "connectors": connectors,
                "refresh_rate_hz": refresh_rate_hz,
                "display_name": display_name,
                "manufacturer": manufacturer,
                "model": model,
                "platform": platform.system(),
                "inventory_source": (
                    ["sysfs DRM", "xrandr"]
                    if platform.system() == "Linux"
                    else ["Windows CIM"]
                ),
                "inventory_status": (
                    "detected"
                    if any(item["status"] == "connected" for item in connectors)
                    else "unsupported"
                    if platform.system() == "Linux" and not LINUX_DRM_ROOT.exists()
                    else "not_detected"
                ),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        result.add_device(device)

        return result


def _read_edid(path: Path) -> dict[str, object] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None

    if len(data) < 128 or data[:8] != b"\x00\xff\xff\xff\xff\xff\xff\x00":
        return None

    vendor_id = int.from_bytes(data[8:10], "big")
    vendor = "".join(
        chr(((vendor_id >> shift) & 0x1F) + 64)
        for shift in (10, 5, 0)
    )
    product_code = int.from_bytes(data[10:12], "little")
    model_name = None

    for offset in range(54, 126, 18):
        descriptor = data[offset : offset + 18]
        if descriptor[:5] != b"\x00\x00\x00\xfc\x00":
            continue
        candidate = descriptor[5:18].decode("ascii", errors="replace")
        model_name = candidate.replace("\n", "").replace("\x00", "").strip()
        break

    year = 1990 + data[17] if data[17] else None
    model = model_name or f"EDID product {product_code:04X}"
    return {
        "manufacturer": vendor if all("A" <= char <= "Z" for char in vendor) else None,
        "product_code": f"{product_code:04X}",
        "model": model,
        "display_name": f"{vendor} {model}".strip() if vendor else model,
        "week_of_manufacture": data[16] or None,
        "year_of_manufacture": year,
        "version": f"{data[18]}.{data[19]}",
    }