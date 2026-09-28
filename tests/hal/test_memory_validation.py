from app.hal.diagnostics.memory_validation import (
    MemoryValidation,
)


def test_memory_validation():
    validator = MemoryValidation()

    checks = validator.validate()

    assert len(checks) == 3

    assert all(
        check.passed
        for check in checks
    )