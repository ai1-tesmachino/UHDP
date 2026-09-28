from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class PrintAction(Action):

    def __init__(
        self,
        message: str,
    ) -> None:
        self.message = message

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        print(self.message)