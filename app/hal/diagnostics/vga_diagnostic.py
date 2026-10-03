from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell
from app.hal.diagnostics.windows_utils import PowerShellUnavailableError
from app.hal.diagnostics.platform_probes import (
    linux_inventory_probe,
    unsupported_result,
)


class VgaDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        probe = linux_inventory_probe(request, "vga")
        if probe is not None:
            return probe
        try:
            connections = run_powershell(
                """
                Get-CimInstance `
                    -Namespace root/wmi `
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
            present = bool(vga_connections)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=(
                    DiagnosticStatus.PASSED
                    if present
                    else DiagnosticStatus.NOT_APPLICABLE
                ),
                message="VGA diagnostic completed",
                details={
                    "vga_present": present,
                    "vga_connection_count": len(
                        vga_connections
                    ),
                    "connections": connections,
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
