from app.hal.diagnostics.network_validation import (
    NetworkValidation,
)


def test_network_validation():
    validator = NetworkValidation()

    checks = validator.validate()

    assert len(checks) == 2

    assert all(
        check.passed
        for check in checks
    )