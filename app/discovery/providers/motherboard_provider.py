import platform
from pathlib import Path
import subprocess

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device

LINUX_DMI_ROOT = Path("/sys/class/dmi/id")


def _read_linux_dmi(name: str) -> str:
    try:
        return (LINUX_DMI_ROOT / name).read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()
    except OSError:
        return ""


class MotherboardProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        manufacturer = ""
        product = ""
        serial_number = ""

        if platform.system() == "Linux":
            manufacturer = _read_linux_dmi("board_vendor")
            product = _read_linux_dmi("board_name")
            serial_number = _read_linux_dmi("board_serial")
        elif platform.system() == "Windows":
            try:
                manufacturer = (
                    subprocess.check_output(
                        ["wmic", "baseboard", "get", "manufacturer", "/value"],
                        text=True,
                    )
                    .split("=")[1]
                    .strip()
                )
            except (OSError, subprocess.SubprocessError, IndexError):
                pass

            try:
                product = (
                    subprocess.check_output(
                        ["wmic", "baseboard", "get", "product", "/value"],
                        text=True,
                    )
                    .split("=")[1]
                    .strip()
                )
            except (OSError, subprocess.SubprocessError, IndexError):
                pass

            try:
                serial_number = (
                    subprocess.check_output(
                        ["wmic", "baseboard", "get", "serialnumber", "/value"],
                        text=True,
                    )
                    .split("=")[1]
                    .strip()
                )
            except (OSError, subprocess.SubprocessError, IndexError):
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