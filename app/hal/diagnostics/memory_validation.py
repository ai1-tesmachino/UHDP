import psutil

from app.hal.models.validation_check import (
    ValidationCheck,
)


class MemoryValidation:

    def validate(
        self,
    ) -> list[ValidationCheck]:
        checks = []

        memory = psutil.virtual_memory()

        checks.append(
            ValidationCheck(
                name="ram_detected",
                passed=memory.total > 0,
                message=str(
                    memory.total,
                ),
            )
        )

        checks.append(
            ValidationCheck(
                name="available_ram",
                passed=(
                    memory.available
                    > 0
                ),
                message=str(
                    memory.available,
                ),
            )
        )

        try:
            block = bytearray(
                1024 * 1024,
            )

            passed = (
                len(block)
                == 1024 * 1024
            )

        except Exception:
            passed = False

        checks.append(
            ValidationCheck(
                name="allocation_test",
                passed=passed,
                message="1MB allocation",
            )
        )

        return checks