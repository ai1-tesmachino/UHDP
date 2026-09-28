import psutil

from app.hal.models.validation_check import (
    ValidationCheck,
)


class CpuValidation:

    def validate(
        self,
    ) -> list[ValidationCheck]:
        checks = []

        logical_cores = psutil.cpu_count(
            logical=True,
        )

        physical_cores = psutil.cpu_count(
            logical=False,
        )

        frequency = psutil.cpu_freq()

        checks.append(
            ValidationCheck(
                name="logical_cores",
                passed=(
                    logical_cores is not None
                    and logical_cores > 0
                ),
                message=str(
                    logical_cores,
                ),
            )
        )

        checks.append(
            ValidationCheck(
                name="physical_cores",
                passed=(
                    physical_cores is not None
                    and physical_cores > 0
                ),
                message=str(
                    physical_cores,
                ),
            )
        )

        checks.append(
            ValidationCheck(
                name="frequency",
                passed=(
                    frequency is not None
                ),
                message=str(
                    frequency.current
                    if frequency
                    else None
                ),
            )
        )

        return checks