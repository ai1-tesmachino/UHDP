from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell
from app.hal.diagnostics.windows_utils import PowerShellUnavailableError
from app.hal.diagnostics.platform_probes import (
    linux_inventory_probe,
    unsupported_result,
)


class KeyboardDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        probe = linux_inventory_probe(request, "keyboard")
        if probe is not None:
            return probe
        try:
            keyboards = run_powershell(
                """
                Get-PnpDevice -Class Keyboard -PresentOnly |
                Select-Object FriendlyName,Status,Class,InstanceId |
                ConvertTo-Json -Compress
                """
            )

            keyboards = as_list(keyboards)
            present = bool(keyboards)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=(
                    DiagnosticStatus.PASSED
                    if present
                    else DiagnosticStatus.NOT_APPLICABLE
                ),
                message="Keyboard diagnostic completed",
                details={
                    "keyboard_present": present,
                    "keyboard_count": len(keyboards),
                    "keyboards": keyboards,
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
