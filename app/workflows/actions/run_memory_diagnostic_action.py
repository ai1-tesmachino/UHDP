from uuid import uuid4

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_service import DiagnosticService
from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class RunMemoryDiagnosticAction(Action):

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        service = DiagnosticService()

        result = service.execute(
            DiagnosticRequest(
                diagnostic_id=str(uuid4()),
                diagnostic_type="memory",
                device_id="local",
            )
        )

        context.set(
            "memory_result",
            result,
        )