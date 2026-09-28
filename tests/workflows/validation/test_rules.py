from app.workflows.validation.rules import (
    WorkflowActionRule,
    WorkflowNameRule,
)


class FakeWorkflow:

    def __init__(
        self,
        name: str = "",
        actions: list[object] | None = None,
    ) -> None:
        self.name = name
        self.actions = actions or []


def test_workflow_name_rule_valid():
    workflow = FakeWorkflow(
        name="Backup Workflow",
    )

    rule = WorkflowNameRule()

    errors = rule.validate(workflow)

    assert errors == []


def test_workflow_name_rule_invalid():
    workflow = FakeWorkflow()

    rule = WorkflowNameRule()

    errors = rule.validate(workflow)

    assert len(errors) == 1
    assert errors[0].code == "missing_workflow_name"


def test_workflow_action_rule_valid():
    workflow = FakeWorkflow(
        name="Test",
        actions=[object()],
    )

    rule = WorkflowActionRule()

    errors = rule.validate(workflow)

    assert errors == []


def test_workflow_action_rule_invalid():
    workflow = FakeWorkflow(
        name="Test",
    )

    rule = WorkflowActionRule()

    errors = rule.validate(workflow)

    assert len(errors) == 1
    assert errors[0].code == "missing_actions"