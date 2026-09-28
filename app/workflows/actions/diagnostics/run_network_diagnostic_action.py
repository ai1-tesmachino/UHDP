from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_service import (
    DiagnosticService,
)
from app.workflows.actions.base import (
    Action,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


class RunNetworkDiagnosticAction(Action):

    def __init__(
        self,
        result_key: str = "network_result",
    ) -> None:
        self._result_key = result_key
        self._service = DiagnosticService()

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        device = self._service.get_device()

        request = DiagnosticRequest(
            diagnostic_type="network",
            device_id=device.device_id,
        )

        result = self._service.execute(
            request,
        )

        context.set(
            self._result_key,
            result,
        )