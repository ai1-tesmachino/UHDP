from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell
from app.hal.diagnostics.windows_utils import PowerShellUnavailableError
from app.hal.diagnostics.platform_probes import (
    linux_inventory_probe,
    unsupported_result,
)


class UsbCDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        probe = linux_inventory_probe(request, "usb_c")
        if probe is not None:
            return probe
        try:
            devices = run_powershell(
                """
                Get-PnpDevice -PresentOnly |
                Where-Object {
                    $_.FriendlyName -match
                    "USB Type-C|USB-C|Type-C|Thunderbolt"
                } |
                Select-Object FriendlyName,Status,Class,InstanceId |
                ConvertTo-Json -Compress
                """
            )

            devices = as_list(devices)
            present = bool(devices)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=(
                    DiagnosticStatus.PASSED
                    if present
                    else DiagnosticStatus.NOT_APPLICABLE
                ),
                message="USB-C diagnostic completed",
                details={
                    "usb_c_device_present": present,
                    "device_count": len(devices),
                    "devices": devices,
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