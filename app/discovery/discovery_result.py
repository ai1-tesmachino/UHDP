
from dataclasses import dataclass, field
from app.discovery.models.device import Device


@dataclass
class DiscoveryResult:
    devices: list[Device] = field(default_factory=list)

    def add_device(
        self,
        device: Device,
    ) -> None:
        self.devices.append(device)