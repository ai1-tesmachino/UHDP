import subprocess

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class MotherboardProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        manufacturer = ""
        product = ""
        serial_number = ""

        try:
            manufacturer = (
                subprocess.check_output(
                    [
                        "wmic",
                        "baseboard",
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
            product = (
                subprocess.check_output(
                    [
                        "wmic",
                        "baseboard",
                        "get",
                        "product",
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
                        "baseboard",
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

        result.add_device(
            Device(
                device_id="motherboard",
                device_type="motherboard",
                name=product or "Motherboard",
                properties={
                    "manufacturer": manufacturer,
                    "product": product,
                    "serial_number": serial_number,
                },
            )
        )

        return result