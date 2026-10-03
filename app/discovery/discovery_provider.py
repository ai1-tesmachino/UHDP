from abc import ABC
from abc import abstractmethod

from app.discovery.discovery_result import DiscoveryResult


class DiscoveryProvider(ABC):

    @abstractmethod
    def discover(self) -> DiscoveryResult:
        pass