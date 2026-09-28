from app.hal.diagnostic_registry import (
    DiagnosticRegistry,
)
from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


class DiagnosticExecutor:

    def __init__(
        self,
        registry: DiagnosticRegistry,
    ) -> None:
        self._registry = registry

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        if not self._registry.exists(
            request.diagnostic_type,
        ):
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.ERROR,
                message=(
                    f"Diagnostic not found: "
                    f"{request.diagnostic_type}"
                ),
            )

        diagnostic = self._registry.get(
            request.diagnostic_type,
        )

        return diagnostic.execute(
            request,
        )