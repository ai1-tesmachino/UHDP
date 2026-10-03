from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell


class WebcamDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

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

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Webcam diagnostic completed",
                details={
                    "webcam_present": len(cameras) > 0,
                    "camera_count": len(cameras),
                    "cameras": cameras,
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
