from app.workflows.actions.base import Action
from app.workflows.exceptions.workflow_failed import (
    WorkflowFailed,
)
from app.workflows.workflow_context import WorkflowContext


class FailAction(Action):

    def __init__(
        self,
        message: str,
    ) -> None:
        self.message = message

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        raise WorkflowFailed(
            self.message,
        )