from app.hal.diagnostics.storage_validation import (
    StorageValidation,
)


def test_storage_validation():
    validator = StorageValidation()

    checks = validator.validate()

    assert len(checks) >= 2

    assert all(
        check.passed
        for check in checks
    )