from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus

from app.workflows.actions.diagnostics.fail_if_diagnostic_failed_action import (
    FailIfDiagnosticFailedAction,
)
from app.workflows.actions.diagnostics.run_cpu_diagnostic_action import (
    RunCpuDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_memory_diagnostic_action import (
    RunMemoryDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_network_diagnostic_action import (
    RunNetworkDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_storage_diagnostic_action import (
    RunStorageDiagnosticAction,
)

from app.workflows.conditions.diagnostic_failed_condition import (
    DiagnosticFailedCondition,
)
from app.workflows.conditions.diagnostic_passed_condition import (
    DiagnosticPassedCondition,
)

from app.workflows.actions.conditional_action import (
    ConditionalAction,
)
from app.workflows.actions.fail_action import (
    FailAction,
)

from app.workflows.workflow import Workflow
from app.workflows.workflow_context import WorkflowContext
from app.workflows.workflow_engine import WorkflowEngine
from app.workflows.workflow_status import WorkflowStatus

from app.workflows.templates.cpu_validation_workflow import (
    create_cpu_validation_workflow,
)
from app.workflows.templates.memory_validation_workflow import (
    create_memory_validation_workflow,
)
from app.workflows.templates.storage_validation_workflow import (
    create_storage_validation_workflow,
)
from app.workflows.templates.network_validation_workflow import (
    create_network_validation_workflow,
)
from app.workflows.templates.full_system_validation_workflow import (
    create_full_system_validation_workflow,
)


def test_cpu_workflow_executes_through_hal():
    workflow = create_cpu_validation_workflow()

    context = WorkflowContext()

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.SUCCESS

    diagnostic_result = context.get(
        "cpu_result",
    )

    assert isinstance(
        diagnostic_result,
        DiagnosticResult,
    )

    assert (
        diagnostic_result.diagnostic_type
        == "cpu"
    )


def test_memory_workflow_executes_through_hal():
    workflow = create_memory_validation_workflow()

    context = WorkflowContext()

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.SUCCESS

    diagnostic_result = context.get(
        "memory_result",
    )

    assert isinstance(
        diagnostic_result,
        DiagnosticResult,
    )

    assert (
        diagnostic_result.diagnostic_type
        == "memory"
    )


def test_storage_workflow_executes_through_hal():
    workflow = create_storage_validation_workflow()

    context = WorkflowContext()

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.SUCCESS

    diagnostic_result = context.get(
        "storage_result",
    )

    assert isinstance(
        diagnostic_result,
        DiagnosticResult,
    )

    assert (
        diagnostic_result.diagnostic_type
        == "storage"
    )


def test_network_workflow_executes_through_hal():
    workflow = create_network_validation_workflow()

    context = WorkflowContext()

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.SUCCESS

    diagnostic_result = context.get(
        "network_result",
    )

    assert isinstance(
        diagnostic_result,
        DiagnosticResult,
    )

    assert (
        diagnostic_result.diagnostic_type
        == "network"
    )


def test_diagnostic_pass_condition():
    context = WorkflowContext()

    context.set(
        "cpu_result",
        DiagnosticResult(
            diagnostic_id="test",
            diagnostic_type="cpu",
            device_id="device",
            status=DiagnosticStatus.PASSED,
        ),
    )

    condition = DiagnosticPassedCondition(
        "cpu_result",
    )

    assert condition.evaluate(
        context,
    ) is True


def test_diagnostic_fail_condition():
    context = WorkflowContext()

    context.set(
        "cpu_result",
        DiagnosticResult(
            diagnostic_id="test",
            diagnostic_type="cpu",
            device_id="device",
            status=DiagnosticStatus.FAILED,
        ),
    )

    condition = DiagnosticFailedCondition(
        "cpu_result",
    )

    assert condition.evaluate(
        context,
    ) is True


def test_workflow_condition_pass_branch():
    context = WorkflowContext()

    context.set(
        "cpu_result",
        DiagnosticResult(
            diagnostic_id="test",
            diagnostic_type="cpu",
            device_id="device",
            status=DiagnosticStatus.PASSED,
        ),
    )

    workflow = Workflow(
        name="cpu_condition_pass",
        actions=[
            ConditionalAction(
                condition=DiagnosticPassedCondition(
                    "cpu_result",
                ),
                true_actions=[],
                false_actions=[
                    FailAction(
                        "CPU diagnostic did not pass",
                    ),
                ],
            ),
        ],
    )

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.SUCCESS


def test_workflow_condition_fail_branch():
    context = WorkflowContext()

    context.set(
        "cpu_result",
        DiagnosticResult(
            diagnostic_id="test",
            diagnostic_type="cpu",
            device_id="device",
            status=DiagnosticStatus.FAILED,
            message="CPU validation failed",
        ),
    )

    workflow = Workflow(
        name="cpu_condition_fail",
        actions=[
            ConditionalAction(
                condition=DiagnosticFailedCondition(
                    "cpu_result",
                ),
                true_actions=[
                    FailAction(
                        "CPU diagnostic failed",
                    ),
                ],
                false_actions=[],
            ),
        ],
    )

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.FAILED


def test_fail_if_diagnostic_failed_action():
    context = WorkflowContext()

    context.set(
        "cpu_result",
        DiagnosticResult(
            diagnostic_id="test",
            diagnostic_type="cpu",
            device_id="device",
            status=DiagnosticStatus.PASSED,
        ),
    )

    workflow = Workflow(
        name="cpu_fail_check",
        actions=[
            FailIfDiagnosticFailedAction(
                result_key="cpu_result",
            ),
        ],
    )

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.SUCCESS


def test_full_system_validation_workflow():
    workflow = (
        create_full_system_validation_workflow()
    )

    context = WorkflowContext()

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.SUCCESS

    assert isinstance(
        context.get("cpu_result"),
        DiagnosticResult,
    )

    assert isinstance(
        context.get("memory_result"),
        DiagnosticResult,
    )

    assert isinstance(
        context.get("storage_result"),
        DiagnosticResult,
    )

    assert isinstance(
        context.get("network_result"),
        DiagnosticResult,
    )