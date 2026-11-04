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


def test_repeated_definition_executions_receive_distinct_run_ids():
    registry = DiagnosticRegistry()
    registry.register("cpu", FakeDiagnostic())
    executor = DiagnosticExecutor(registry)
    request = DiagnosticRequest(diagnostic_type="cpu", device_id="local")

    first = executor.execute(request)
    second = executor.execute(request)

    assert first.diagnostic_id == second.diagnostic_id == "cpu"
    assert first.run_id != second.run_id
    assert request.run_id == second.run_id


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


def test_unexpected_diagnostic_exception_is_an_explicit_error():
    class RaisingDiagnostic:
        def execute(self, request):
            raise PermissionError("device access denied")

    registry = DiagnosticRegistry()
    registry.register("cpu", RaisingDiagnostic())
    result = DiagnosticExecutor(registry).execute(
        DiagnosticRequest(diagnostic_type="cpu", device_id="device-1")
    )

    assert result.status is DiagnosticStatus.ERROR
    assert result.details == {
        "exception_type": "PermissionError",
        "exception_message": "device access denied",
    }
    assert "PermissionError" in result.message