from app.workflows.context import (
    WorkflowContext,
)
from app.workflows.actions.run_manual_diagnostic_action import (
    RunManualDiagnosticAction,
)
from app.workflows.manual.manual_test_registry import (
    ManualTestRegistry,
)


def test_manual_action():

    registry = ManualTestRegistry()

    action = (
        RunManualDiagnosticAction(
            registry=registry,
            test_name="keyboard",
            passed=True,
            notes="all keys working",
        )
    )

    context = WorkflowContext()

    action.execute(
        context,
    )

    result = registry.get(
        "keyboard",
    )

    assert result is not None
    assert result.passed is True

    stored = context.get(
        "manual.keyboard",
    )

    assert stored is not None