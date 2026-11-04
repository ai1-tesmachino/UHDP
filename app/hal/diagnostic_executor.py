from uuid import uuid4

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
        request.run_id = str(uuid4())
        run_id = request.run_id
        if not self._registry.exists(
            request.diagnostic_type,
        ):
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id or request.diagnostic_type,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.ERROR,
                run_id=run_id,
                message=(
                    f"Diagnostic not found: "
                    f"{request.diagnostic_type}"
                ),
            )

        diagnostic = self._registry.get(
            request.diagnostic_type,
        )

        try:
            result = diagnostic.execute(request)
            result.diagnostic_id = (
                request.diagnostic_id or request.diagnostic_type
            )
            result.run_id = run_id
            return result
        except Exception as exc:
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id or request.diagnostic_type,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.ERROR,
                run_id=run_id,
                message=(
                    f"{request.diagnostic_type} diagnostic raised "
                    f"{type(exc).__name__}: {exc}"
                ),
                details={
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
            )