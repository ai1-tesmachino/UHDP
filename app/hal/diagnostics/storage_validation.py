from pathlib import Path
from uuid import uuid4

from app.hal.models.validation_check import (
    ValidationCheck,
)


class StorageValidation:

    def validate(
        self,
    ) -> list[ValidationCheck]:
        checks = []

        file_path = (
            Path.cwd()
            / f"uhdp_{uuid4()}.tmp"
        )

        content = (
            "UHDP_STORAGE_TEST"
        )

        try:
            file_path.write_text(
                content,
                encoding="utf-8",
            )

            checks.append(
                ValidationCheck(
                    name="write_test",
                    passed=True,
                    message="file written",
                )
            )

            read_content = (
                file_path.read_text(
                    encoding="utf-8",
                )
            )

            checks.append(
                ValidationCheck(
                    name="read_test",
                    passed=(
                        read_content
                        == content
                    ),
                    message="file read",
                )
            )

        except Exception as ex:
            checks.append(
                ValidationCheck(
                    name="storage_test",
                    passed=False,
                    message=str(ex),
                )
            )

        finally:
            if file_path.exists():
                file_path.unlink()

        return checks