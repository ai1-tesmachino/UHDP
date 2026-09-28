import platform
import socket

from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


class SystemDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        try:
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="System diagnostic completed",
                details={
                    "hostname": socket.gethostname(),
                    "operating_system": platform.system(),
                    "os_version": platform.version(),
                    "architecture": platform.machine(),
                    "processor": platform.processor(),
                    "python_version": platform.python_version(),
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