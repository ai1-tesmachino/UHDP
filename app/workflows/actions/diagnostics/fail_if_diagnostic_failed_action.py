from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.workflows.actions.base import (
    Action,
)
from app.workflows.exceptions.workflow_failed import (
    WorkflowFailed,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


class FailIfDiagnosticFailedAction(Action):

    def __init__(
        self,
        result_key: str,
        message: str | None = None,
    ) -> None:
        self.result_key = result_key
        self.message = message

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        result = context.get(
            self.result_key,
        )

        if result is None:
            raise WorkflowFailed(
                f"Diagnostic result not found: {self.result_key}"
            )

        if result.status in (
            DiagnosticStatus.FAILED,
            DiagnosticStatus.ERROR,
        ):
            raise WorkflowFailed(
                self.message
                or result.message
                or "Diagnostic failed"
            )