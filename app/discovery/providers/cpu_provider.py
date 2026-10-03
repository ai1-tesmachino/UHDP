import platform

import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class CPUProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        cpu_name = platform.processor()
        if not cpu_name and platform.system() == "Linux":
            try:
                with open(
                    "/proc/cpuinfo",
                    encoding="utf-8",
                    errors="replace",
                ) as cpuinfo:
                    for line in cpuinfo:
                        if line.lower().startswith("model name"):
                            cpu_name = line.split(":", 1)[-1].strip()
                            break
            except OSError:
                pass

        if not cpu_name:
            cpu_name = platform.machine()

        frequency = psutil.cpu_freq()
        instruction_sets = []
        if platform.system() == "Linux":
            try:
                with open(
                    "/proc/cpuinfo",
                    encoding="utf-8",
                    errors="replace",
                ) as cpuinfo:
                    for line in cpuinfo:
                        if line.lower().startswith(("flags", "features")):
                            instruction_sets = line.split(":", 1)[-1].split()
                            break
            except OSError:
                instruction_sets = []
        device = Device(
            device_id="cpu",
            device_type="cpu",
            name=cpu_name,
            properties={
                "physical_cores": psutil.cpu_count(
                    logical=False,
                ),
                "logical_cores": psutil.cpu_count(
                    logical=True,
                ),
                "architecture": platform.machine(),
                "instruction_sets": instruction_sets,
                "vendor": platform.processor() or None,
                "minimum_frequency_mhz": (
                    round(frequency.min, 2)
                    if frequency and frequency.min
                    else None
                ),
                "current_frequency_mhz": (
                    round(frequency.current, 2)
                    if frequency
                    else None
                ),
                "max_frequency_mhz": (
                    round(frequency.max, 2)
                    if frequency and frequency.max
                    else None
                ),
                "platform": platform.platform(),
            },
        )

        result.add_device(device)

        return result