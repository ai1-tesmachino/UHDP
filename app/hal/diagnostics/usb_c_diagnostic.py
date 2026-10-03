from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell


class UsbCDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

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

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="USB-C diagnostic completed",
                details={
                    "usb_c_device_present": len(devices) > 0,
                    "device_count": len(devices),
                    "devices": devices,
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