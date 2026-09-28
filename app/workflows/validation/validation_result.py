from collections.abc import Iterable

from app.workflows.validation.validation_error import (
    ValidationError,
)


class ValidationResult:

    def __init__(
        self,
        errors: Iterable[ValidationError] | None = None,
    ) -> None:
        self._errors = list(errors or [])

    @property
    def errors(
        self,
    ) -> list[ValidationError]:
        return list(self._errors)

    @property
    def is_valid(
        self,
    ) -> bool:
        return not self._errors

    def add_error(
        self,
        error: ValidationError,
    ) -> None:
        self._errors.append(error)

    def extend(
        self,
        errors: Iterable[ValidationError],
    ) -> None:
        self._errors.extend(errors)