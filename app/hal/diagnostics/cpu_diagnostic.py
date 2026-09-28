import platform

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


class CpuDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        try:
            frequency = psutil.cpu_freq()

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="CPU diagnostic completed",
                details={
                    "processor": platform.processor(),
                    "architecture": platform.machine(),
                    "logical_cores": psutil.cpu_count(
                        logical=True,
                    ),
                    "physical_cores": psutil.cpu_count(
                        logical=False,
                    ),
                    "cpu_usage_percent": psutil.cpu_percent(
                        interval=0.1,
                    ),
                    "current_frequency_mhz": (
                        frequency.current
                        if frequency
                        else None
                    ),
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