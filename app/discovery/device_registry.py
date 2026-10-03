from app.discovery.models.device import Device


class DeviceRegistry:

    def __init__(self) -> None:
        self._devices: dict[str, Device] = {}

    def register(
        self,
        device: Device,
    ) -> None:
        self._devices[device.device_id] = device

    def register_all(
        self,
        devices: list[Device],
    ) -> None:
        for device in devices:
            self.register(device)

    def get(
        self,
        device_id: str,
    ) -> Device | None:
        return self._devices.get(device_id)

    def all(self) -> list[Device]:
        return list(self._devices.values())

    def clear(self) -> None:
        self._devices.clear()