from dataclasses import dataclass


@dataclass(slots=True)
class DeviceInfo:
    device_id: str
    hostname: str
    operating_system: str
    architecture: str