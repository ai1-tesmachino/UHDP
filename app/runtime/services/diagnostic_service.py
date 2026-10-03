from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_service import (
    DiagnosticService as HalDiagnosticService,
)


class DiagnosticService:

    def __init__(
        self,
        diagnostic_service: HalDiagnosticService | None = None,
    ) -> None:
        self._service = (
            diagnostic_service
            or HalDiagnosticService()
        )
    def list_diagnostics(self) -> list[str]:
        return self._service.registry.list_diagnostics()

    def execute(
        self,
        diagnostic_type: str,
        device_id: str | None = None,
        parameters: dict[str, object] | None = None,
    ) -> DiagnosticResult:
        if device_id is None:
            device = (
                self._service.get_device()
            )

            device_id = device.device_id

        request = DiagnosticRequest(
            diagnostic_type=diagnostic_type,
            device_id=device_id,
            parameters=parameters or {},
        )

        return self._service.execute(
            request,
        )