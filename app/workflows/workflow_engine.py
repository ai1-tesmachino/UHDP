from app.workflows.exceptions.workflow_failed import (
    WorkflowFailed,
)
from app.workflows.exceptions.workflow_stopped import (
    WorkflowStopped,
)

from app.workflows.workflow_context import (
    WorkflowContext,
)

from app.workflows.workflow_result import (
    WorkflowResult,
)

from app.workflows.workflow_status import (
    WorkflowStatus,
)


class WorkflowEngine:

    def execute(
        self,
        workflow,
        context: WorkflowContext | None = None,
    ) -> WorkflowResult:

        context = context or WorkflowContext()

        try:

            for action in workflow.actions:
                action.execute(context)

            return WorkflowResult(
                status=WorkflowStatus.SUCCESS,
            )

        except WorkflowStopped:

            return WorkflowResult(
                status=WorkflowStatus.STOPPED,
            )

        except WorkflowFailed as exc:

            return WorkflowResult(
                status=WorkflowStatus.FAILED,
                message=str(exc),
            )