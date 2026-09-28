from app.hal.diagnostic_executor import (
    DiagnosticExecutor,
)
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


class FakeDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        return DiagnosticResult(
            diagnostic_id=request.diagnostic_id,
            diagnostic_type=request.diagnostic_type,
            device_id=request.device_id,
            status=DiagnosticStatus.PASSED,
            message="success",
        )


def test_execute_registered_diagnostic():
    registry = DiagnosticRegistry()

    registry.register(
        "cpu",
        FakeDiagnostic(),
    )

    executor = DiagnosticExecutor(
        registry,
    )

    request = DiagnosticRequest(
        diagnostic_type="cpu",
        device_id="local",
    )

    result = executor.execute(
        request,
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )

    assert result.message == "success"


def test_execute_unknown_diagnostic():
    registry = DiagnosticRegistry()

    executor = DiagnosticExecutor(
        registry,
    )

    request = DiagnosticRequest(
        diagnostic_type="unknown",
        device_id="local",
    )

    result = executor.execute(
        request,
    )

    assert (
        result.status
        == DiagnosticStatus.ERROR
    )

    assert (
        "Diagnostic not found"
        in result.message
    )