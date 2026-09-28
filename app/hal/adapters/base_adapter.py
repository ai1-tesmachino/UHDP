from abc import ABC
from abc import abstractmethod

from app.hal.device_info import DeviceInfo


class BaseAdapter(ABC):

    @abstractmethod
    def discover_device(
        self,
    ) -> DeviceInfo:
        pass