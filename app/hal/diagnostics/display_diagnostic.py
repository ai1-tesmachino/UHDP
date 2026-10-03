from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell
from app.hal.diagnostics.windows_utils import PowerShellUnavailableError
from app.hal.diagnostics.platform_probes import (
    linux_inventory_probe,
    unsupported_result,
)


class DisplayDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        probe = linux_inventory_probe(request, "display")
        if probe is not None:
            return probe
        try:
            displays = run_powershell(
                """
                Get-CimInstance Win32_DesktopMonitor |
                Select-Object Name,PNPDeviceID,Status |
                ConvertTo-Json -Compress
                """
            )

            displays = as_list(displays)
            present = bool(displays)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=(
                    DiagnosticStatus.PASSED
                    if present
                    else DiagnosticStatus.NOT_APPLICABLE
                ),
                message="Display diagnostic completed",
                details={
                    "display_present": present,
                    "display_count": len(displays),
                    "displays": displays,
                },
            )

        except PowerShellUnavailableError as ex:
            return unsupported_result(request, str(ex))
        except Exception as ex:
            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.ERROR,
                message=str(ex),
            )
