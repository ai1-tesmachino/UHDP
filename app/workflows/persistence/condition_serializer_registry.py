from __future__ import annotations

from app.workflows.conditions.base import Condition
from app.workflows.persistence.condition_serializer import (
    ConditionSerializer,
)


class ConditionSerializerRegistry:

    def __init__(self) -> None:
        self._serializers: dict[
            str,
            ConditionSerializer,
        ] = {}

    def register(
        self,
        serializer: ConditionSerializer,
    ) -> None:
        self._serializers[
            serializer.condition_type
        ] = serializer

    def get(
        self,
        condition_type: str,
    ) -> ConditionSerializer:
        serializer = self._serializers.get(
            condition_type
        )

        if serializer is None:
            raise ValueError(
                f"No serializer registered for "
                f"condition type: {condition_type}"
            )

        return serializer

    def get_for_condition(
        self,
        condition: Condition,
    ) -> ConditionSerializer:
        return self.get(
            type(condition).__name__
        )

    def exists(
        self,
        condition_type: str,
    ) -> bool:
        return condition_type in self._serializers