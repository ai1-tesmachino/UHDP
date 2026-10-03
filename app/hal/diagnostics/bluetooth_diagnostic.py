from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell


class BluetoothDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        try:
            adapters = run_powershell(
                """
                Get-PnpDevice -Class Bluetooth -PresentOnly |
                Select-Object FriendlyName,Status,Class,InstanceId |
                ConvertTo-Json -Compress
                """
            )

            adapters = as_list(adapters)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Bluetooth diagnostic completed",
                details={
                    "bluetooth_present": len(adapters) > 0,
                    "adapter_count": len(adapters),
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
