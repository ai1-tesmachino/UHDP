from abc import ABC, abstractmethod
from typing import Any


class Action(ABC):
    @abstractmethod
    def execute(self, context: Any) -> Any:
        raise NotImplementedError