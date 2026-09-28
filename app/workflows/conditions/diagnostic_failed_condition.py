from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.workflows.conditions.base import (
    Condition,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


class DiagnosticFailedCondition(Condition):

    def __init__(
        self,
        result_key: str,
    ) -> None:
        self.result_key = result_key

    def evaluate(
        self,
        context: WorkflowContext,
    ) -> bool:
        result = context.get(
            self.result_key,
        )

        if result is None:
            return False

        return result.status in (
            DiagnosticStatus.FAILED,
            DiagnosticStatus.ERROR,
        )