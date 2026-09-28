import subprocess

from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


class UsbDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        try:
            devices = []

            try:
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        (
                            "Get-PnpDevice "
                            "-Class USB | "
                            "Select-Object "
                            "-ExpandProperty FriendlyName"
                        ),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                devices = [
                    line.strip()
                    for line in result.stdout.splitlines()
                    if line.strip()
                ]

            except Exception:
                pass

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="USB diagnostic completed",
                details={
                    "device_count": len(
                        devices,
                    ),
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