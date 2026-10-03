from app.workflows.manual.manual_test_definition import (
    ManualTestDefinition,
)
from app.workflows.manual.manual_test_manager import (
    ManualTestManager,
)
from app.workflows.manual.manual_test_result import (
    ManualTestResult,
)


def test_register_and_get_manual_test_definition():
    manager = ManualTestManager()

    definition = ManualTestDefinition(
        test_name="keyboard",
        description="Verify keyboard keys",
    )

    manager.register(definition)

    assert manager.get("keyboard") == definition


def test_all_returns_registered_definitions():
    manager = ManualTestManager()

    keyboard = ManualTestDefinition(
        test_name="keyboard",
    )
    display = ManualTestDefinition(
        test_name="display",
    )

    manager.register(keyboard)
    manager.register(display)

    assert manager.all() == [
        keyboard,
        display,
    ]


def test_record_and_get_result():
    manager = ManualTestManager()

    result = ManualTestResult(
        test_name="keyboard",
        passed=True,
        notes="All keys working",
    )

    manager.record(result)

    assert manager.result("keyboard") == result


def test_results_returns_all_results():
    manager = ManualTestManager()

    keyboard = ManualTestResult(
        test_name="keyboard",
        passed=True,
    )
    display = ManualTestResult(
        test_name="display",
        passed=False,
        notes="Dead pixel",
    )

    manager.record(keyboard)
    manager.record(display)

    assert manager.results() == [
        keyboard,
        display,
    ]