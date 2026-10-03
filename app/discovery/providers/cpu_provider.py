import platform
import uuid

import psutil

from app.discovery.discovery_provider import DiscoveryProvider
from app.discovery.discovery_result import DiscoveryResult
from app.discovery.models.device import Device


class CPUProvider(DiscoveryProvider):

    def discover(self) -> DiscoveryResult:
        result = DiscoveryResult()

        cpu_name = platform.processor()

        if not cpu_name:
            cpu_name = platform.machine()

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
                "platform": platform.platform(),
            },
        )

        result.add_device(device)

        return result