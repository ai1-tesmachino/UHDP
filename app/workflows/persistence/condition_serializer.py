from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from app.workflows.conditions.base import Condition


class ConditionSerializer(ABC):

    @property
    @abstractmethod
    def condition_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def serialize(
        self,
        condition: Condition,
    ) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def deserialize(
        self,
        data: dict[str, object],
    ) -> Condition:
        raise NotImplementedError