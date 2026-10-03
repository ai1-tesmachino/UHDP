from app.workflows.manual.manual_test_registry import (
    ManualTestRegistry,
)
from app.workflows.manual.manual_test_result import (
    ManualTestResult,
)


def test_record_manual_result():

    registry = ManualTestRegistry()

    registry.record(
        ManualTestResult(
            test_name="keyboard",
            passed=True,
        )
    )

    result = registry.get(
        "keyboard",
    )

    assert result is not None
    assert result.passed is True


def test_list_results():

    registry = ManualTestRegistry()

    registry.record(
        ManualTestResult(
            test_name="display",
            passed=True,
        )
    )

    assert len(
        registry.all()
    ) == 1