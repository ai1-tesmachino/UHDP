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

    def execute(
        self,
        diagnostic_type: str,
    ) -> DiagnosticResult:
        device = (
            self._service.get_device()
        )

        request = DiagnosticRequest(
            diagnostic_type=diagnostic_type,
            device_id=device.device_id,
        )

        return self._service.execute(
            request,
        )