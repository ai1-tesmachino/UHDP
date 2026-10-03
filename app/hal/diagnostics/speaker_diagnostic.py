
from app.hal.diagnostic_request import DiagnosticRequest
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus
from app.hal.diagnostics.windows_utils import as_list, run_powershell


class SpeakerDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:

        try:
            speakers = run_powershell(
                """
                Get-CimInstance Win32_SoundDevice |
                Select-Object Name,Status,PNPDeviceID |
                ConvertTo-Json -Compress
                """
            )

            speakers = as_list(speakers)

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Speaker diagnostic completed",
                details={
                    "speaker_present": len(speakers) > 0,
                    "speaker_count": len(speakers),
                    "speakers": speakers,
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
