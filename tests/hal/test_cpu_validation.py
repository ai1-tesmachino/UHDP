from app.hal.diagnostics.cpu_validation import (
    CpuValidation,
)


def test_cpu_validation():
    validator = CpuValidation()

    checks = validator.validate()

    assert len(checks) == 3

    assert all(
        check.passed
        for check in checks
    )