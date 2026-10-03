from unittest.mock import patch

import pytest

from app.hal.default_diagnostics import create_default_registry
from app.hal.diagnostic_result import DiagnosticResult
from app.hal.diagnostic_status import DiagnosticStatus

from app.workflows.workflow_context import WorkflowContext
from app.workflows.workflow_engine import WorkflowEngine
from app.workflows.workflow_status import WorkflowStatus

from app.workflows.templates.full_system_validation_workflow import (
    DIAGNOSTIC_ACTIONS,
    create_full_system_validation_workflow,
)


def test_every_registered_diagnostic_has_a_workflow_action():
    registry = create_default_registry()

    assert set(registry.list_diagnostics()) == set(DIAGNOSTIC_ACTIONS)


def test_system_diagnostic_is_included_in_workflow():
    workflow = create_full_system_validation_workflow(
        selected_diagnostics=["system"]
    )

    assert len(workflow.actions) == 2
    assert workflow.actions[0].__class__.__name__ == "RunSystemDiagnosticAction"


def test_unknown_diagnostic_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported diagnostic: unknown",
    ):
        create_full_system_validation_workflow(
            selected_diagnostics=["unknown"]
        )


def test_full_system_validation_workflow_passes():
    workflow = (
        create_full_system_validation_workflow()
    )

    context = WorkflowContext()

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status == WorkflowStatus.SUCCESS

    assert (
        context.get("cpu_result").status
        == DiagnosticStatus.PASSED
    )

    assert (
        context.get("memory_result").status
        == DiagnosticStatus.PASSED
    )

    assert (
        context.get("storage_result").status
        == DiagnosticStatus.PASSED
    )

    assert (
        context.get("network_result").status
        == DiagnosticStatus.PASSED
    )


def test_full_system_validation_stops_on_failed_cpu():
    failed_cpu_result = DiagnosticResult(
        diagnostic_id="cpu-test",
        diagnostic_type="cpu",
        device_id="device",
        status=DiagnosticStatus.FAILED,
        message="CPU diagnostic failed",
    )

    with patch(
        "app.workflows.actions.diagnostics.run_cpu_diagnostic_action.DiagnosticService"
    ) as service_class:

        service = service_class.return_value
        service.get_device.return_value.device_id = "device"
        service.execute.return_value = (
            failed_cpu_result
        )

        workflow = (
            create_full_system_validation_workflow()
        )

        context = WorkflowContext()

        result = WorkflowEngine().execute(
            workflow,
            context,
        )

    assert result.status == WorkflowStatus.FAILED

    assert (
        context.exists("cpu_result")
        is True
    )

    assert (
        context.exists("memory_result")
        is False
    )

    assert (
        context.exists("storage_result")
        is False
    )

    assert (
        context.exists("network_result")
        is False
    )


def test_full_system_validation_stops_on_failed_memory():
    failed_memory_result = DiagnosticResult(
        diagnostic_id="memory-test",
        diagnostic_type="memory",
        device_id="device",
        status=DiagnosticStatus.FAILED,
        message="Memory diagnostic failed",
    )

    with patch(
        "app.workflows.actions.diagnostics.run_memory_diagnostic_action.DiagnosticService"
    ) as service_class:

        service = service_class.return_value
        service.get_device.return_value.device_id = "device"
        service.execute.return_value = (
            failed_memory_result
        )

        workflow = (
            create_full_system_validation_workflow()
        )

        context = WorkflowContext()

        result = WorkflowEngine().execute(
            workflow,
            context,
        )

    assert result.status == WorkflowStatus.FAILED

    assert (
        context.exists("cpu_result")
        is True
    )

    assert (
        context.exists("memory_result")
        is True
    )

    assert (
        context.exists("storage_result")
        is False
    )

    assert (
        context.exists("network_result")
        is False
    )