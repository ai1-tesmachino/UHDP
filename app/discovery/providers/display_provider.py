import platform
import re
import shutil
import subprocess
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
                connectors.append({
                    "name": connector.name,
                    "status": status,
                    "modes": modes,
                })
                if status == "connected":
                    display_modes.extend(modes)
            if display_modes:
                resolution = display_modes[0]
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
                "platform": platform.system(),
            },
        )

        result.add_device(device)

        return result