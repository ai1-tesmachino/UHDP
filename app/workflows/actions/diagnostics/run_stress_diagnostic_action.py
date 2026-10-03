from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_service import DiagnosticService
from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class RunStressDiagnosticAction(Action):
    def __init__(
        self,
        diagnostic_type: str,
        result_key: str,
        duration_seconds: int = 10,
    ) -> None:
        self._diagnostic_type = diagnostic_type
        self._result_key = result_key
        self._duration_seconds = min(30, max(1, duration_seconds))
        self._service = DiagnosticService()

    def execute(self, context: WorkflowContext) -> None:
        device = self._service.get_device()
        result = self._service.execute(
            DiagnosticRequest(
                diagnostic_type=self._diagnostic_type,
                device_id=device.device_id,
                parameters={"duration_seconds": self._duration_seconds},
            )
        )
        context.set(self._result_key, result)
