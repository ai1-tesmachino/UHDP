from app.workflows.actions.base import Action
from app.workflows.exceptions.workflow_stopped import (
    WorkflowStopped,
)
from app.workflows.workflow_context import WorkflowContext


class StopAction(Action):

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        raise WorkflowStopped()