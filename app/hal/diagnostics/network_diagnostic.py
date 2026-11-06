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
                status=DiagnosticStatus.INCONCLUSIVE,
                message=(
                    "Network adapter inventory completed; connectivity was not tested"
                ),
                details={
                    "adapter_count": len(
                        adapters,
                    ),
                    "adapters": adapters,
                    "connectivity_verified": False,
                },
            )
        except Exception as ex:
            permission_denied = isinstance(ex, PermissionError)
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=(
                    DiagnosticStatus.INCONCLUSIVE
                    if permission_denied
                    else DiagnosticStatus.ERROR
                ),
                message=(
                    f"Permission denied while enumerating network interfaces: {ex}"
                    if permission_denied
                    else str(ex)
                ),
                details=(
                    {
                        "error_category": "permission_denied",
                        "scan_status": "error",
                    }
                    if permission_denied
                    else {}
                ),
            )