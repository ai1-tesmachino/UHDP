import json
import subprocess

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class NetworkProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        adapters = []

        try:
            command = """
            Get-NetAdapter |
            Select Name,
                   Status,
                   MacAddress,
                   LinkSpeed |
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
                adapters = json.loads(
                    response.stdout
                )

                if isinstance(
                    adapters,
                    dict,
                ):
                    adapters = [adapters]

        except Exception:
            pass

        result.add_device(
            Device(
                device_id="network",
                device_type="network",
                name="Network Adapters",
                properties={
                    "adapter_count": len(
                        adapters
                    ),
                    "adapters": adapters,
                },
            )
        )

        return result