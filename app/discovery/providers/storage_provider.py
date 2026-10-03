import platform
import uuid
import json
import subprocess
import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class StorageProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        seen_devices: set[str] = set()

        disk_details = {}

        try:
            command = """
            Get-PhysicalDisk |
            Select-Object FriendlyName,
                        SerialNumber,
                        Size,
                        MediaType |
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

                disks = json.loads(
                    result_json.stdout,
                )

                if isinstance(
                    disks,
                    dict,
                ):
                    disks = [disks]

                for disk in disks:
                    disk_details[
                        disk.get(
                            "FriendlyName",
                            "",
                        )
                    ] = disk

        except Exception as ex:
            disk_details = {
                "error": {
                    "message": str(ex),
                }
            }



        for partition in psutil.disk_partitions(
            all=False,
        ):
            device_name = partition.device

            if device_name in seen_devices:
                continue

            seen_devices.add(device_name)

            try:
                usage = psutil.disk_usage(
                    partition.mountpoint,
                )
            except (
                PermissionError,
                OSError,
            ):
                continue

            device = Device(
                device_id=f"storage:{device_name}",
                device_type="storage",
                name=device_name,
                properties={
                    "device": device_name,
                    "mountpoint": partition.mountpoint,
                    "filesystem": partition.fstype,
                    "total_bytes": usage.total,
                    "used_bytes": usage.used,
                    "free_bytes": usage.free,
                    "percent_used": usage.percent,
                    "total_gb": round(
                        usage.total / (1024 ** 3),
                        2,
                    ),
                    "physical_disks": list(
                        disk_details.values()
                    ),
                    "platform": platform.platform(),
                },
            )

            result.add_device(device)

        return result