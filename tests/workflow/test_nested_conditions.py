from app.workflows.actions.conditional_action import (
    ConditionalAction,
)
from app.workflows.actions.set_variable_action import (
    SetVariableAction,
)

from app.workflows.conditions.greater_than_condition import (
    GreaterThanCondition,
)

from app.workflows.workflow_context import (
    WorkflowContext,
)


def test_nested_conditions():

    context = WorkflowContext()

    context.set(
        "score",
        95,
    )

    workflow_action = ConditionalAction(
        condition=GreaterThanCondition(
            "score",
            50,
        ),
        true_actions=[
            SetVariableAction(
                "passed",
                True,
            ),
            ConditionalAction(
                condition=GreaterThanCondition(
                    "score",
                    90,
                ),
                true_actions=[
                    SetVariableAction(
                        "distinction",
                        True,
                    ),
                ],
            ),
        ],
    )

    workflow_action.execute(
        context,
    )

    assert context.get(
        "passed"
    ) is True

    assert context.get(
        "distinction"
    ) is True