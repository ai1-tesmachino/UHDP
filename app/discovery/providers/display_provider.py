import subprocess

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class DisplayProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        resolution = "Unknown"

        try:
            output = subprocess.check_output(
                [
                    "powershell",
                    "-Command",
                    "(Get-CimInstance Win32_VideoController | Select-Object -First 1 CurrentHorizontalResolution,CurrentVerticalResolution | ConvertTo-Json -Compress)"
                ],
                text=True,
            )

            import json

            data = json.loads(output)

            width = data.get(
                "CurrentHorizontalResolution",
            )

            height = data.get(
                "CurrentVerticalResolution",
            )

            if width and height:
                resolution = f"{width}x{height}"

        except Exception:
            pass

        device = Device(
            device_id="display",
            device_type="display",
            name="Display",
            properties={
                "resolution": resolution,
            },
        )

        result.add_device(device)

        return result