from app.workflows.conditions.equals_condition import (
    EqualsCondition,
)
from app.workflows.workflow_context import WorkflowContext


def test_equals_condition_true():

    context = WorkflowContext()

    context.set(
        "name",
        "Alice",
    )

    condition = EqualsCondition(
        "name",
        "Alice",
    )

    assert condition.evaluate(context) is True


def test_equals_condition_false():

    context = WorkflowContext()

    context.set(
        "name",
        "Bob",
    )

    condition = EqualsCondition(
        "name",
        "Alice",
    )

    assert condition.evaluate(context) is False