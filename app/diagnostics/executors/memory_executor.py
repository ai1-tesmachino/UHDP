import psutil

from app.diagnostics.models.diagnostic_result import (
    DiagnosticResult,
)
from app.diagnostics.models.diagnostic_status import (
    DiagnosticStatus,
)


class MemoryExecutor:

    def execute(
        self,
    ) -> DiagnosticResult:

        try:
            memory = psutil.virtual_memory()

            return DiagnosticResult(
                test_name="memory",
                status=DiagnosticStatus.PASSED,
                message="Memory diagnostic completed",
                details={
                    "total_gb": round(
                        memory.total / 1024**3,
                        2,
                    ),
                    "available_gb": round(
                        memory.available / 1024**3,
                        2,
                    ),
                    "usage_percent": (
                        memory.percent
                    ),
                },
            )

        except Exception as ex:
            return DiagnosticResult(
                test_name="memory",
                status=DiagnosticStatus.ERROR,
                message=str(ex),
            )