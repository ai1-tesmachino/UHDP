from app.workflows.actions.run_manual_test_action import (
    RunManualTestAction,
)
from app.workflows.manual.manual_test_manager import (
    ManualTestManager,
)
from app.workflows.workflow_context import WorkflowContext


def test_run_manual_test_action_records_result():
    manager = ManualTestManager()
    context = WorkflowContext()

    action = RunManualTestAction(
        manager=manager,
        test_name="keyboard",
        passed=True,
        notes="All keys working",
    )

    action.execute(context)

    result = manager.result("keyboard")

    assert result is not None
    assert result.test_name == "keyboard"
    assert result.passed is True
    assert result.notes == "All keys working"


def test_run_manual_test_action_stores_result_in_context():
    manager = ManualTestManager()
    context = WorkflowContext()

    action = RunManualTestAction(
        manager=manager,
        test_name="display",
        passed=False,
        notes="Dead pixel detected",
    )

    action.execute(context)

    result = context.get("manual.display")

    assert result is not None
    assert result.test_name == "display"
    assert result.passed is False
    assert result.notes == "Dead pixel detected"