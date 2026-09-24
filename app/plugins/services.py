from abc import ABC
from abc import abstractmethod


class PluginService(ABC):
    name: str

    @abstractmethod
    async def execute(
        self,
        **kwargs,
    ):
        pass