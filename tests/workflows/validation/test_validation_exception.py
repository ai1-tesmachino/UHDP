from app.workflows.validation.validation_error import (
    ValidationError,
)

from app.workflows.validation.validation_exception import (
    ValidationException,
)

from app.workflows.validation.validation_result import (
    ValidationResult,
)


def test_validation_exception_contains_message():
    result = ValidationResult(
        [
            ValidationError(
                code="error",
                message="failure",
            ),
        ],
    )

    exception = ValidationException(
        result
    )

    assert exception.result is result
    assert "failure" in str(
        exception
    )