from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from app.plugins.models import PluginMetadata


class BasePlugin(ABC):
    metadata: PluginMetadata

    def __init__(self) -> None:
        self.services: list = []
        self.runtime = None

    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass

Plugin = BasePlugin