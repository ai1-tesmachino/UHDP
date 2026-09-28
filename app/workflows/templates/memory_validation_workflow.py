from app.workflows.actions.diagnostics.run_memory_diagnostic_action import (
    RunMemoryDiagnosticAction,
)
from app.workflows.workflow import (
    Workflow,
)


def create_memory_validation_workflow() -> Workflow:
    return Workflow(
        name="memory_validation_workflow",
        actions=[
            RunMemoryDiagnosticAction(),
        ],
    )