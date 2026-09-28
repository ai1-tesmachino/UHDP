import platform
import socket
from uuid import uuid4

from app.hal.adapters.base_adapter import (
    BaseAdapter,
)
from app.hal.device_info import DeviceInfo


class LocalAdapter(BaseAdapter):

    def discover_device(
        self,
    ) -> DeviceInfo:
        return DeviceInfo(
            device_id=str(uuid4()),
            hostname=socket.gethostname(),
            operating_system=platform.system(),
            architecture=platform.machine(),
        )