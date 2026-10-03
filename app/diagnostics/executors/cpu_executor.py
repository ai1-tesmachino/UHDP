import psutil

from app.diagnostics.models.diagnostic_result import (
    DiagnosticResult,
)
from app.diagnostics.models.diagnostic_status import (
    DiagnosticStatus,
)


class CpuExecutor:

    def execute(
        self,
    ) -> DiagnosticResult:

        try:
            usage = psutil.cpu_percent(
                interval=1,
            )

            return DiagnosticResult(
                test_name="cpu",
                status=DiagnosticStatus.PASSED,
                message="CPU diagnostic completed",
                details={
                    "cpu_usage_percent": usage,
                    "physical_cores": psutil.cpu_count(
                        logical=False,
                    ),
                    "logical_cores": psutil.cpu_count(
                        logical=True,
                    ),
                },
            )

        except Exception as ex:
            return DiagnosticResult(
                test_name="cpu",
                status=DiagnosticStatus.ERROR,
                message=str(ex),
            )