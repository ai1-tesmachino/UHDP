import pytest

from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.workflows.actions.diagnostics.fail_if_diagnostic_failed_action import (
    FailIfDiagnosticFailedAction,
)
from app.workflows.exceptions.workflow_failed import (
    WorkflowFailed,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


def test_fail_if_diagnostic_failed_action_passed():
    context = WorkflowContext()

    context.set(
        "result",
        DiagnosticResult(
            diagnostic_id="1",
            diagnostic_type="cpu",
            device_id="device",
            status=DiagnosticStatus.PASSED,
        ),
    )

    action = FailIfDiagnosticFailedAction(
        "result",
    )

    action.execute(
        context,
    )


def test_fail_if_diagnostic_failed_action_failed():
    context = WorkflowContext()

    context.set(
        "result",
        DiagnosticResult(
            diagnostic_id="1",
            diagnostic_type="cpu",
            device_id="device",
            status=DiagnosticStatus.FAILED,
        ),
    )

    action = FailIfDiagnosticFailedAction(
        "result",
    )

    with pytest.raises(
        WorkflowFailed,
    ):
        action.execute(
            context,
        )