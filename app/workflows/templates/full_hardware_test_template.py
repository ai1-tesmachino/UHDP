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
from app.workflows.actions.save_report_action import (
    SaveReportAction,
)
from app.workflows.workflow import (
    Workflow,
)


def create_full_hardware_test_workflow() -> Workflow:

    return Workflow(
        name="full_hardware_test",
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

            SaveReportAction(
                "full_hardware_test",
            ),
        ],
    )