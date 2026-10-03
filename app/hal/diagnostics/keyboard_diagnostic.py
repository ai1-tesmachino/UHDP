from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell


class KeyboardDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        try:
            keyboards = run_powershell(
                """
                Get-PnpDevice -Class Keyboard -PresentOnly |
                Select-Object FriendlyName,Status,Class,InstanceId |
                ConvertTo-Json -Compress
                """
            )

            keyboards = as_list(keyboards)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Keyboard diagnostic completed",
                details={
                    "keyboard_present": len(keyboards) > 0,
                    "keyboard_count": len(keyboards),
                    "keyboards": keyboards,
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
