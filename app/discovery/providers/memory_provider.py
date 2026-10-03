import json
import platform
import subprocess

import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class MemoryProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        memory = psutil.virtual_memory()

        modules = []

        try:
            command = """
            Get-CimInstance Win32_PhysicalMemory |
            Select-Object Manufacturer,
                        PartNumber,
                        SerialNumber,
                        Capacity,
                        Speed,
                        BankLabel |
            ConvertTo-Json -Compress
            """

            result_json = subprocess.run(
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
                check=False,
            )

            if result_json.returncode == 0:
                data = json.loads(
                    result_json.stdout,
                )

                if isinstance(
                    data,
                    dict,
                ):
                    data = [data]

                modules = data
            else:
                modules = [
                    {
                        "stderr": result_json.stderr,
                    }
                ]

        except Exception as ex:
            modules = [
                {
                    "error": str(ex),
                }
            ]

        device = Device(
            device_id="memory",
            device_type="memory",
            name="System Memory",
            properties={
                "total_bytes": memory.total,
                "available_bytes": memory.available,
                "used_bytes": memory.used,
                "free_bytes": memory.free,
                "percent_used": memory.percent,
                "total_gb": round(
                    memory.total / (1024**3),
                    2,
                ),
                "memory_modules": modules,
                "platform": platform.platform(),
            },
        )

        result.add_device(device)

        return result