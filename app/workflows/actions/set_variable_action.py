from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class SetVariableAction(Action):

    def __init__(
        self,
        key: str,
        value,
    ) -> None:
        self.key = key
        self.value = value

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        context.set(
            self.key,
            self.value,
        )