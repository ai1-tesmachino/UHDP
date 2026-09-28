from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.workflows.actions.diagnostics.store_diagnostic_result_action import (
    StoreDiagnosticResultAction,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


def test_store_diagnostic_result_action():
    context = WorkflowContext()

    result = DiagnosticResult(
        diagnostic_id="1",
        diagnostic_type="cpu",
        device_id="device",
        status=DiagnosticStatus.PASSED,
    )

    context.set(
        "cpu_result",
        result,
    )

    action = StoreDiagnosticResultAction(
        source_key="cpu_result",
        target_key="saved_result",
    )

    action.execute(
        context,
    )

    assert (
        context.get("saved_result")
        is result
    )