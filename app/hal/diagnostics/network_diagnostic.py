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


class NetworkDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        try:
            adapters = []

            interfaces = psutil.net_if_addrs()

            for name, addresses in interfaces.items():
                adapters.append(
                    {
                        "name": name,
                        "address_count": len(
                            addresses,
                        ),
                    }
                )

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Network diagnostic completed",
                details={
                    "adapter_count": len(
                        adapters,
                    ),
                    "adapters": adapters,
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