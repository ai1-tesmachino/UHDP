from app.workflows.validation.validation_error import (
    ValidationError,
)
from app.workflows.validation.validation_result import (
    ValidationResult,
)


def test_empty_result_is_valid():
    result = ValidationResult()

    assert result.is_valid is True
    assert result.errors == []


def test_result_with_error_is_invalid():
    result = ValidationResult()

    result.add_error(
        ValidationError(
            code="error",
            message="failure",
        ),
    )

    assert result.is_valid is False
    assert len(result.errors) == 1


def test_extend_errors():
    result = ValidationResult()

    result.extend(
        [
            ValidationError(
                code="a",
                message="a",
            ),
            ValidationError(
                code="b",
                message="b",
            ),
        ],
    )

    assert len(result.errors) == 2
    assert result.is_valid is False