from app.hal.adapters.base_adapter import (
    BaseAdapter,
)
from app.hal.device_info import DeviceInfo


class DeviceManager:

    def __init__(
        self,
        adapter: BaseAdapter,
    ) -> None:
        self._adapter = adapter

    def get_device(
        self,
    ) -> DeviceInfo:
        return self._adapter.discover_device()