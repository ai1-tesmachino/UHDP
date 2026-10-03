from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_service import DiagnosticService
from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class RunWifiDiagnosticAction(Action):

    def __init__(
        self,
        result_key: str = "wifi_result",
    ) -> None:
        self._result_key = result_key
        self._service = DiagnosticService()

    def execute(self, context: WorkflowContext) -> None:
        device = self._service.get_device()

        result = self._service.execute(
            DiagnosticRequest(
                diagnostic_type="wifi",
                device_id=device.device_id,
            )
        )

        context.set(self._result_key, result)
