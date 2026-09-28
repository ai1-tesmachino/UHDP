from app.workflows.actions.diagnostics.run_storage_diagnostic_action import (
    RunStorageDiagnosticAction,
)
from app.workflows.workflow import (
    Workflow,
)


def create_storage_validation_workflow() -> Workflow:
    return Workflow(
        name="storage_validation_workflow",
        actions=[
            RunStorageDiagnosticAction(),
        ],
    )