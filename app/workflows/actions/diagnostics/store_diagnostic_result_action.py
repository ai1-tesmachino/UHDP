from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class StoreDiagnosticResultAction(Action):

    def __init__(
        self,
        source_key: str,
        target_key: str,
    ) -> None:
        self.source_key = source_key
        self.target_key = target_key

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        result = context.get(
            self.source_key,
        )

        context.set(
            self.target_key,
            result,
        )