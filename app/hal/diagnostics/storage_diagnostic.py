from pathlib import Path

import psutil

from app.hal.diagnostic_request import (
    DiagnosticRequest,
)
from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)


class StorageDiagnostic:

    def execute(
        self,
        request: DiagnosticRequest,
    ) -> DiagnosticResult:
        try:
            drives = []

            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(
                        partition.mountpoint,
                    )

                    drives.append(
                        {
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "filesystem": partition.fstype,
                            "total_gb": round(
                                usage.total / 1024**3,
                                2,
                            ),
                            "free_gb": round(
                                usage.free / 1024**3,
                                2,
                            ),
                            "used_percent": usage.percent,
                        }
                    )
                except PermissionError:
                    continue

            return DiagnosticResult(
                diagnostic_id=request.diagnostic_id,
                diagnostic_type=request.diagnostic_type,
                device_id=request.device_id,
                status=DiagnosticStatus.PASSED,
                message="Storage diagnostic completed",
                details={
                    "current_directory": str(
                        Path.cwd(),
                    ),
                    "drives": drives,
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