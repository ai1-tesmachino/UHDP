from app.workflows.actions.base import Action
from app.workflows.conditions.base import Condition
from app.workflows.workflow_context import WorkflowContext


class ConditionalAction(Action):

    def __init__(
        self,
        condition: Condition,
        true_actions: list[Action] | None = None,
        false_actions: list[Action] | None = None,
    ) -> None:
        self.condition = condition
        self.true_actions = true_actions or []
        self.false_actions = false_actions or []

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        actions = (
            self.true_actions
            if self.condition.evaluate(context)
            else self.false_actions
        )

        for action in actions:
            action.execute(context)