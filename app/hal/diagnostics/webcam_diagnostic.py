from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell
from app.hal.diagnostics.windows_utils import PowerShellUnavailableError
from app.hal.diagnostics.platform_probes import (
    linux_inventory_probe,
    unsupported_result,
)


class WebcamDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        probe = linux_inventory_probe(request, "webcam")
        if probe is not None:
            return probe
        try:
            cameras = run_powershell(
                """
                Get-PnpDevice -PresentOnly |
                Where-Object {
                    $_.Class -eq "Camera" -or
                    $_.FriendlyName -match "Camera|Webcam"
                } |
                Select-Object FriendlyName,Status,Class,InstanceId |
                ConvertTo-Json -Compress
                """
            )

            cameras = as_list(cameras)
            present = bool(cameras)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=(
                    DiagnosticStatus.PASSED
                    if present
                    else DiagnosticStatus.NOT_APPLICABLE
                ),
                message="Webcam diagnostic completed",
                details={
                    "webcam_present": present,
                    "camera_count": len(cameras),
                    "cameras": cameras,
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
