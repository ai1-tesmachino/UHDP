from pathlib import Path

import psutil

from app.diagnostics.models.diagnostic_result import (
    DiagnosticResult,
)
from app.diagnostics.models.diagnostic_status import (
    DiagnosticStatus,
)


class StorageExecutor:

    def execute(
        self,
    ) -> DiagnosticResult:

        try:
            drives = []

            for partition in (
                psutil.disk_partitions()
            ):
                try:
                    usage = (
                        psutil.disk_usage(
                            partition.mountpoint,
                        )
                    )

                    drives.append(
                        {
                            "device": (
                                partition.device
                            ),
                            "filesystem": (
                                partition.fstype
                            ),
                            "free_gb": round(
                                usage.free
                                / 1024**3,
                                2,
                            ),
                            "used_percent": (
                                usage.percent
                            ),
                        }
                    )

                except PermissionError:
                    continue

            return DiagnosticResult(
                test_name="storage",
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
                test_name="storage",
                status=DiagnosticStatus.ERROR,
                message=str(ex),
            )