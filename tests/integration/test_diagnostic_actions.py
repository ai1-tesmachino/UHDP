from app.workflows.workflow_context import (
    WorkflowContext,
)

from app.workflows.actions.diagnostics.run_cpu_diagnostic_action import (
    RunCpuDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_memory_diagnostic_action import (
    RunMemoryDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_storage_diagnostic_action import (
    RunStorageDiagnosticAction,
)
from app.workflows.actions.diagnostics.run_network_diagnostic_action import (
    RunNetworkDiagnosticAction,
)

from app.hal.diagnostic_result import (
    DiagnosticResult,
)


def test_run_cpu_diagnostic_action():
    context = WorkflowContext()

    action = RunCpuDiagnosticAction()

    action.execute(
        context,
    )

    result = context.get(
        "cpu_result",
    )

    assert isinstance(
        result,
        DiagnosticResult,
    )


def test_run_memory_diagnostic_action():
    context = WorkflowContext()

    action = RunMemoryDiagnosticAction()

    action.execute(
        context,
    )

    result = context.get(
        "memory_result",
    )

    assert isinstance(
        result,
        DiagnosticResult,
    )


def test_run_storage_diagnostic_action():
    context = WorkflowContext()

    action = RunStorageDiagnosticAction()

    action.execute(
        context,
    )

    result = context.get(
        "storage_result",
    )

    assert isinstance(
        result,
        DiagnosticResult,
    )


def test_run_network_diagnostic_action():
    context = WorkflowContext()

    action = RunNetworkDiagnosticAction()

    action.execute(
        context,
    )

    result = context.get(
        "network_result",
    )

    assert isinstance(
        result,
        DiagnosticResult,
    )