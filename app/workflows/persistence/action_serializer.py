from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from app.workflows.actions.base import Action


class ActionSerializer(ABC):

    @property
    @abstractmethod
    def action_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def serialize(
        self,
        action: Action,
    ) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def deserialize(
        self,
        data: dict[str, object],
    ) -> Action:
        raise NotImplementedError