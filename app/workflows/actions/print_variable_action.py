from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class PrintVariableAction(Action):

    def __init__(
        self,
        key: str,
    ) -> None:
        self.key = key

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        print(
            context.get(self.key)
        )