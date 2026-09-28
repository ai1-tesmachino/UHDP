from app.workflows.validation.validation_error import ValidationError


def test_validation_error_properties():
    error = ValidationError(
        code="missing_name",
        message="Workflow name is required.",
        path="name",
    )

    assert error.code == "missing_name"
    assert error.message == "Workflow name is required."
    assert error.path == "name"