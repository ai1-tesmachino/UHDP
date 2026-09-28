from app.hal.diagnostics.base_diagnostic import (
    BaseDiagnostic,
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


class TestDiagnostic(
    BaseDiagnostic,
):

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        return DiagnosticResult(
            diagnostic_id=request.diagnostic_id,
            diagnostic_type=request.diagnostic_type,
            device_id=request.device_id,
            status=DiagnosticStatus.PASSED,
        )


def test_base_diagnostic():
    diagnostic = TestDiagnostic()

    result = diagnostic.execute(
        DiagnosticRequest(
            diagnostic_type="test",
            device_id="device",
        )
    )

    assert (
        result.status
        == DiagnosticStatus.PASSED
    )