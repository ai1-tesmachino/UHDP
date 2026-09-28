from app.hal.diagnostic_result import (
    DiagnosticResult,
)
from app.hal.diagnostic_status import (
    DiagnosticStatus,
)
from app.workflows.conditions.diagnostic_failed_condition import (
    DiagnosticFailedCondition,
)
from app.workflows.conditions.diagnostic_passed_condition import (
    DiagnosticPassedCondition,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


def test_diagnostic_passed_condition():
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

    condition = DiagnosticPassedCondition(
        "result",
    )

    assert (
        condition.evaluate(context)
        is True
    )


def test_diagnostic_failed_condition():
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

    condition = DiagnosticFailedCondition(
        "result",
    )

    assert (
        condition.evaluate(context)
        is True
    )