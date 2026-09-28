from app.workflows.actions.conditional_action import (
    ConditionalAction,
)
from app.workflows.actions.set_variable_action import (
    SetVariableAction,
)
from app.workflows.conditions.equals_condition import (
    EqualsCondition,
)
from app.workflows.workflow_context import WorkflowContext


def test_conditional_action():

    context = WorkflowContext()

    context.set(
        "status",
        "new",
    )

    action = ConditionalAction(
        condition=EqualsCondition(
            "status",
            "new",
        ),
        true_actions=[
            SetVariableAction(
                "result",
                "success",
            ),
        ],
    )

    action.execute(context)

    assert (
        context.get("result")
        == "success"
    )