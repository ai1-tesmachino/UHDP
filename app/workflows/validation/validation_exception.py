from app.workflows.validation.validation_result import (
    ValidationResult,
)


class ValidationException(Exception):

    def __init__(
        self,
        result: ValidationResult,
    ) -> None:
        self.result = result

        super().__init__(
            self._build_message(),
        )

    def _build_message(
        self,
    ) -> str:
        return "\n".join(
            error.message
            for error in self.result.errors
        )