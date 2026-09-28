from app.workflows.actions.diagnostics.fail_if_diagnostic_failed_action import (
    FailIfDiagnosticFailedAction,
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

from app.workflows.workflow import Workflow


def create_full_system_validation_workflow() -> Workflow:
    return Workflow(
        name="full_system_validation_workflow",
        actions=[
            RunCpuDiagnosticAction(),
            FailIfDiagnosticFailedAction(
                result_key="cpu_result",
                message="CPU diagnostic failed",
            ),

            RunMemoryDiagnosticAction(),
            FailIfDiagnosticFailedAction(
                result_key="memory_result",
                message="Memory diagnostic failed",
            ),

            RunStorageDiagnosticAction(),
            FailIfDiagnosticFailedAction(
                result_key="storage_result",
                message="Storage diagnostic failed",
            ),

            RunNetworkDiagnosticAction(),
            FailIfDiagnosticFailedAction(
                result_key="network_result",
                message="Network diagnostic failed",
            ),
        ],
    )