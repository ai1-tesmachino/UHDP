import time

from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.stress_utils import stress_test_duration


class CpuStressDiagnostic:
    def execute(self, request: DiagnosticRequest) -> DiagnosticResult:
        duration = stress_test_duration(request)
        deadline = time.monotonic() + duration
        iterations = 0
        value = 1

        while time.monotonic() < deadline:
            value = (value * 1_664_525 + 1_013_904_223) & 0xFFFFFFFF
            iterations += 1

        return DiagnosticResult(
            diagnostic_id=request.diagnostic_id,
            diagnostic_type=request.diagnostic_type,
            device_id=request.device_id,
            status=DiagnosticStatus.PASSED,
            message="Bounded CPU load completed",
            details={
                "duration_seconds": duration,
                "iterations": iterations,
                "cpu_cores_used": 1,
                "stress_test": True,
            },
        )
