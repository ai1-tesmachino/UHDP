from __future__ import annotations

from app.workflows.actions.base import Action
from app.workflows.actions.conditional_action import (
    ConditionalAction,
)
from app.workflows.actions.fail_action import (
    FailAction,
)
from app.workflows.actions.foreach import (
    ForEachAction,
)
from app.workflows.actions.print_action import (
    PrintAction,
)
from app.workflows.actions.print_variable_action import (
    PrintVariableAction,
)
from app.workflows.actions.set_variable_action import (
    SetVariableAction,
)
from app.workflows.actions.stop_action import (
    StopAction,
)

from app.workflows.conditions.base import Condition
from app.workflows.conditions.equals_condition import (
    EqualsCondition,
)
from app.workflows.conditions.greater_than_condition import (
    GreaterThanCondition,
)
from app.workflows.conditions.less_than_condition import (
    LessThanCondition,
)
from app.workflows.conditions.not_equals_condition import (
    NotEqualsCondition,
)

from app.workflows.persistence.action_serializer import (
    ActionSerializer,
)
from app.workflows.persistence.condition_serializer import (
    ConditionSerializer,
)
from app.workflows.persistence.serializer_registry import (
    SerializerRegistry,
)
from app.workflows.persistence.condition_serializer_registry import (
    ConditionSerializerRegistry,
)
from app.workflows.persistence.serializer import (
    WorkflowSerializer,
)


class PrintActionSerializer(ActionSerializer):

    @property
    def action_type(self) -> str:
        return "PrintAction"

    def serialize(
        self,
        action: Action,
    ) -> dict[str, object]:
        action = action

        return {
            "message": action.message,
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Action:
        return PrintAction(
            data["message"],
        )


class SetVariableActionSerializer(
    ActionSerializer,
):

    @property
    def action_type(self) -> str:
        return "SetVariableAction"

    def serialize(
        self,
        action: Action,
    ) -> dict[str, object]:
        return {
            "key": action.key,
            "value": action.value,
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Action:
        return SetVariableAction(
            key=data["key"],
            value=data["value"],
        )


class PrintVariableActionSerializer(
    ActionSerializer,
):

    @property
    def action_type(self) -> str:
        return "PrintVariableAction"

    def serialize(
        self,
        action: Action,
    ) -> dict[str, object]:
        return {
            "key": action.key,
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Action:
        return PrintVariableAction(
            data["key"],
        )


class FailActionSerializer(
    ActionSerializer,
):

    @property
    def action_type(self) -> str:
        return "FailAction"

    def serialize(
        self,
        action: Action,
    ) -> dict[str, object]:
        return {
            "message": action.message,
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Action:
        return FailAction(
            data["message"],
        )


class StopActionSerializer(
    ActionSerializer,
):

    @property
    def action_type(self) -> str:
        return "StopAction"

    def serialize(
        self,
        action: Action,
    ) -> dict[str, object]:
        return {}

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Action:
        return StopAction()


class ConditionalActionSerializer(
    ActionSerializer,
):

    def __init__(
        self,
        workflow_serializer: WorkflowSerializer,
    ) -> None:
        self._workflow_serializer = (
            workflow_serializer
        )

    @property
    def action_type(self) -> str:
        return "ConditionalAction"

    def serialize(
        self,
        action: Action,
    ) -> dict[str, object]:
        action = action

        return {
            "condition": (
                self._workflow_serializer
                .serialize_condition(
                    action.condition
                )
            ),
            "true_actions": [
                self._workflow_serializer
                .serialize_action(
                    nested_action
                )
                for nested_action
                in action.true_actions
            ],
            "false_actions": [
                self._workflow_serializer
                .serialize_action(
                    nested_action
                )
                for nested_action
                in action.false_actions
            ],
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Action:
        condition = (
            self._workflow_serializer
            .deserialize_condition(
                data["condition"]
            )
        )

        true_actions = [
            self._workflow_serializer
            .deserialize_action(
                nested_action
            )
            for nested_action
            in data.get(
                "true_actions",
                [],
            )
        ]

        false_actions = [
            self._workflow_serializer
            .deserialize_action(
                nested_action
            )
            for nested_action
            in data.get(
                "false_actions",
                [],
            )
        ]

        return ConditionalAction(
            condition=condition,
            true_actions=true_actions,
            false_actions=false_actions,
        )


class ForEachActionSerializer(
    ActionSerializer,
):

    def __init__(
        self,
        workflow_serializer: WorkflowSerializer,
    ) -> None:
        self._workflow_serializer = (
            workflow_serializer
        )

    @property
    def action_type(self) -> str:
        return "ForEachAction"

    def serialize(
        self,
        action: Action,
    ) -> dict[str, object]:
        return {
            "collection_name": (
                action.collection_name
            ),
            "item_name": action.item_name,
            "actions": [
                self._workflow_serializer
                .serialize_action(
                    nested_action
                )
                for nested_action
                in action.actions
            ],
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Action:
        actions = [
            self._workflow_serializer
            .deserialize_action(
                nested_action
            )
            for nested_action
            in data.get(
                "actions",
                [],
            )
        ]

        return ForEachAction(
            collection_name=data[
                "collection_name"
            ],
            item_name=data[
                "item_name"
            ],
            actions=actions,
        )


class EqualsConditionSerializer(
    ConditionSerializer,
):

    @property
    def condition_type(self) -> str:
        return "EqualsCondition"

    def serialize(
        self,
        condition: Condition,
    ) -> dict[str, object]:
        return {
            "variable_name": (
                condition.variable_name
            ),
            "expected_value": (
                condition.expected_value
            ),
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Condition:
        return EqualsCondition(
            variable_name=data[
                "variable_name"
            ],
            expected_value=data[
                "expected_value"
            ],
        )


class NotEqualsConditionSerializer(
    ConditionSerializer,
):

    @property
    def condition_type(self) -> str:
        return "NotEqualsCondition"

    def serialize(
        self,
        condition: Condition,
    ) -> dict[str, object]:
        return {
            "variable_name": (
                condition.variable_name
            ),
            "expected_value": (
                condition.expected_value
            ),
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Condition:
        return NotEqualsCondition(
            variable_name=data[
                "variable_name"
            ],
            expected_value=data[
                "expected_value"
            ],
        )


class GreaterThanConditionSerializer(
    ConditionSerializer,
):

    @property
    def condition_type(self) -> str:
        return "GreaterThanCondition"

    def serialize(
        self,
        condition: Condition,
    ) -> dict[str, object]:
        return {
            "variable_name": (
                condition.variable_name
            ),
            "value": condition.value,
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Condition:
        return GreaterThanCondition(
            variable_name=data[
                "variable_name"
            ],
            value=data["value"],
        )


class LessThanConditionSerializer(
    ConditionSerializer,
):

    @property
    def condition_type(self) -> str:
        return "LessThanCondition"

    def serialize(
        self,
        condition: Condition,
    ) -> dict[str, object]:
        return {
            "variable_name": (
                condition.variable_name
            ),
            "value": condition.value,
        }

    def deserialize(
        self,
        data: dict[str, object],
    ) -> Condition:
        return LessThanCondition(
            variable_name=data[
                "variable_name"
            ],
            value=data["value"],
        )

def create_default_registry() -> SerializerRegistry:
    action_registry = SerializerRegistry()

    condition_registry = (
        ConditionSerializerRegistry()
    )

    serializer = WorkflowSerializer(
        action_registry=action_registry,
        condition_registry=condition_registry,
    )

    action_registry.register(
        PrintActionSerializer()
    )

    action_registry.register(
        SetVariableActionSerializer()
    )

    action_registry.register(
        PrintVariableActionSerializer()
    )

    action_registry.register(
        FailActionSerializer()
    )

    action_registry.register(
        StopActionSerializer()
    )

    action_registry.register(
        ConditionalActionSerializer(
            serializer
        )
    )

    action_registry.register(
        ForEachActionSerializer(
            serializer
        )
    )

    condition_registry.register(
        EqualsConditionSerializer()
    )

    condition_registry.register(
        NotEqualsConditionSerializer()
    )

    condition_registry.register(
        GreaterThanConditionSerializer()
    )

    condition_registry.register(
        LessThanConditionSerializer()
    )

    return action_registry

def create_default_serializer() -> WorkflowSerializer:
    action_registry = (
        create_default_registry()
    )

    condition_registry = (
        action_registry.condition_registry
    )

    return WorkflowSerializer(
        action_registry=action_registry,
        condition_registry=condition_registry,
    )