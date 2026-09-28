import psutil

from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


class MemoryDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        try:
            memory = psutil.virtual_memory()

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Memory diagnostic completed",
                details={
                    "total_ram_mb": round(
                        memory.total / 1024 / 1024,
                        2,
                    ),
                    "available_ram_mb": round(
                        memory.available / 1024 / 1024,
                        2,
                    ),
                    "used_ram_mb": round(
                        memory.used / 1024 / 1024,
                        2,
                    ),
                    "usage_percent": memory.percent,
                },
            )
        except Exception as ex:
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.ERROR,
                message=str(ex),
            )