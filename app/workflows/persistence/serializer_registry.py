from __future__ import annotations

from app.workflows.actions.base import Action

from app.workflows.persistence.action_serializer import (
    ActionSerializer,
)


class SerializerRegistry:

    def __init__(self) -> None:
        self._serializers: dict[
            str,
            ActionSerializer,
        ] = {}

        self.condition_registry = None

    def register(
        self,
        serializer: ActionSerializer,
    ) -> None:
        self._serializers[
            serializer.action_type
        ] = serializer

    def get(
        self,
        action_type: str,
    ) -> ActionSerializer:

        serializer = self._serializers.get(
            action_type
        )

        if serializer is None:
            raise ValueError(
                f"No serializer registered "
                f"for action type: "
                f"{action_type}"
            )

        return serializer

    def get_for_action(
        self,
        action: Action,
    ) -> ActionSerializer:
        return self.get(
            type(action).__name__
        )

    def exists(
        self,
        action_type: str,
    ) -> bool:
        return (
            action_type
            in self._serializers
        )
