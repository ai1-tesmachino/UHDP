from abc import ABC
from abc import abstractmethod

from app.plugins.models import PluginMetadata


class BasePlugin(ABC):
    metadata: PluginMetadata

    services: list = []

    runtime = None

    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass