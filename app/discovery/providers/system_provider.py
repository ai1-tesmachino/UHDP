import json
import socket
import subprocess

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class SystemProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        manufacturer = ""
        model = ""
        serial_number = ""
        bios_version = ""

        try:
            manufacturer = (
                subprocess.check_output(
                    [
                        "wmic",
                        "computersystem",
                        "get",
                        "manufacturer",
                        "/value",
                    ],
                    text=True,
                )
                .split("=")[1]
                .strip()
            )
        except Exception:
            pass

        try:
            model = (
                subprocess.check_output(
                    [
                        "wmic",
                        "computersystem",
                        "get",
                        "model",
                        "/value",
                    ],
                    text=True,
                )
                .split("=")[1]
                .strip()
            )
        except Exception:
            pass

        try:
            serial_number = (
                subprocess.check_output(
                    [
                        "wmic",
                        "bios",
                        "get",
                        "serialnumber",
                        "/value",
                    ],
                    text=True,
                )
                .split("=")[1]
                .strip()
            )
        except Exception:
            pass

        try:
            bios_version = (
                subprocess.check_output(
                    [
                        "wmic",
                        "bios",
                        "get",
                        "smbiosbiosversion",
                        "/value",
                    ],
                    text=True,
                )
                .split("=")[1]
                .strip()
            )
        except Exception:
            pass

        device = Device(
            device_id="system",
            device_type="system",
            name=f"{manufacturer} {model}".strip(),
            properties={
                "hostname": socket.gethostname(),
                "manufacturer": manufacturer,
                "model": model,
                "serial_number": serial_number,
                "bios_version": bios_version,
            },
        )

        result.add_device(device)

        return result