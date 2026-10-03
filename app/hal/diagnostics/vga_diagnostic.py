from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell


class VgaDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        try:
            connections = run_powershell(
                """
                Get-CimInstance
                -Namespace root/wmi
                -ClassName WmiMonitorConnectionParams |
                Select-Object InstanceName,Active,VideoOutputTechnology |
                ConvertTo-Json -Compress
                """
            )

            connections = as_list(connections)

            vga_connections = [
                item
                for item in connections
                if str(
                    item.get(
                        "VideoOutputTechnology",
                        "",
                    )
                ) == "5"
            ]

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="VGA diagnostic completed",
                details={
                    "vga_present": len(vga_connections) > 0,
                    "vga_connection_count": len(
                        vga_connections
                    ),
                    "connections": connections,
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
