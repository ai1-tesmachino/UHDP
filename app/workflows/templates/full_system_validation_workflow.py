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
from app.workflows.workflow import (
    Workflow,
)


def create_full_system_validation_workflow() -> Workflow:
    return Workflow(
        name="full_system_validation_workflow",
        actions=[
            RunCpuDiagnosticAction(),
            RunMemoryDiagnosticAction(),
            RunStorageDiagnosticAction(),
            RunNetworkDiagnosticAction(),
        ],
    )