import json
import subprocess

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class BatteryProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        battery = {}

        try:
            command = """
            Get-CimInstance Win32_Battery |
            Select Name,
                   Status,
                   EstimatedChargeRemaining,
                   DesignVoltage |
            ConvertTo-Json -Compress
            """

            response = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    command,
                ],
                capture_output=True,
                text=True,
            )

            if response.returncode == 0:
                battery = json.loads(
                    response.stdout
                )

        except Exception:
            pass

        result.add_device(
            Device(
                device_id="battery",
                device_type="battery",
                name="Battery",
                properties=battery,
            )
        )

        return result