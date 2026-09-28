from app.workflows.actions.build_report_action import (
    BuildReportAction,
)
from app.workflows.actions.run_cpu_diagnostic_action import (
    RunCpuDiagnosticAction,
)
from app.workflows.actions.run_cpu_validation_action import (
    RunCpuValidationAction,
)
from app.workflows.actions.run_memory_diagnostic_action import (
    RunMemoryDiagnosticAction,
)
from app.workflows.actions.run_memory_validation_action import (
    RunMemoryValidationAction,
)
from app.workflows.actions.run_network_diagnostic_action import (
    RunNetworkDiagnosticAction,
)
from app.workflows.actions.run_network_validation_action import (
    RunNetworkValidationAction,
)
from app.workflows.actions.run_storage_diagnostic_action import (
    RunStorageDiagnosticAction,
)
from app.workflows.actions.run_storage_validation_action import (
    RunStorageValidationAction,
)
from app.workflows.workflow import Workflow
from app.workflows.workflow_context import (
    WorkflowContext,
)
from app.workflows.workflow_engine import (
    WorkflowEngine,
)


def test_hardware_workflow():

    workflow = Workflow(
        name="hardware_test",
        actions=[
            RunCpuDiagnosticAction(),
            RunMemoryDiagnosticAction(),
            RunStorageDiagnosticAction(),
            RunNetworkDiagnosticAction(),
            RunCpuValidationAction(),
            RunMemoryValidationAction(),
            RunStorageValidationAction(),
            RunNetworkValidationAction(),
            BuildReportAction(),
        ],
    )

    context = WorkflowContext()

    result = WorkflowEngine().execute(
        workflow,
        context,
    )

    assert result.status.value == "success"

    assert context.exists(
        "diagnostic_report",
    )