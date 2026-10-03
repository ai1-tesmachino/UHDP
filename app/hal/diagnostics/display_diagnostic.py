from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell


class DisplayDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        try:
            displays = run_powershell(
                """
                Get-CimInstance Win32_DesktopMonitor |
                Select-Object Name,PNPDeviceID,Status |
                ConvertTo-Json -Compress
                """
            )

            displays = as_list(displays)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Display diagnostic completed",
                details={
                    "display_present": len(displays) > 0,
                    "display_count": len(displays),
                    "displays": displays,
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
