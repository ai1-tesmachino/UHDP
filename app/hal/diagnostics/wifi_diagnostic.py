from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell


class WifiDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        try:
            adapters = run_powershell(
                """
                Get-NetAdapter -Physical |
                Where-Object {
                    $_.Name -match
                    "Wi-Fi|WiFi|Wireless" -or
                    $_.InterfaceDescription -match
                    "Wi-Fi|WiFi|Wireless|802.11"
                } |
                Select-Object Name,InterfaceDescription,
                Status,LinkSpeed,MacAddress |
                ConvertTo-Json -Compress
                """
            )

            adapters = as_list(adapters)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Wi-Fi diagnostic completed",
                details={
                    "wifi_adapter_present": len(adapters) > 0,
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
