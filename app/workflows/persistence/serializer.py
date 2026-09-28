from __future__ import annotations

from app.workflows.actions.base import Action
from app.workflows.conditions.base import Condition
from app.workflows.workflow import Workflow


class WorkflowSerializer:

    def __init__(
        self,
        action_registry=None,
        condition_registry=None,
    ) -> None:
        self._action_registry = (
            action_registry
        )

        self._condition_registry = (
            condition_registry
        )

    def serialize(
        self,
        workflow: Workflow,
    ) -> dict[str, object]:

        if self._action_registry is None:
            return {
                "name": workflow.name,
                "actions": [],
            }

        return {
            "name": workflow.name,
            "actions": [
                self.serialize_action(action)
                for action in workflow.actions
            ],
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Workflow:

        if self._action_registry is None:
            return Workflow(
                name=data["name"],
                actions=[],
            )

        actions = [
            self.deserialize_action(
                action_data
            )
            for action_data in data.get(
                "actions",
                [],
            )
        ]

        return Workflow(
            name=data["name"],
            actions=actions,
        )

    def serialize_action(
        self,
        action: Action,
    ) -> dict[str, object]:

        serializer = (
            self._action_registry
            .get_for_action(action)
        )

        return {
            "type": serializer.action_type,
            "config": serializer.serialize(
                action
            ),
        }

    def deserialize_action(
        self,
        data: dict[str, object],
    ) -> Action:

        serializer = (
            self._action_registry.get(
                data["type"]
            )
        )

        return serializer.deserialize(
            data.get(
                "config",
                {},
            )
        )

    def serialize_condition(
        self,
        condition: Condition,
    ) -> dict[str, object]:

        serializer = (
            self._condition_registry
            .get_for_condition(
                condition
            )
        )

        return {
            "type": (
                serializer.condition_type
            ),
            "config": serializer.serialize(
                condition
            ),
        }

    def deserialize_condition(
        self,
        data: dict[str, object],
    ) -> Condition:

        serializer = (
            self._condition_registry.get(
                data["type"]
            )
        )

        return serializer.deserialize(
            data.get(
                "config",
                {},
            )
        )

