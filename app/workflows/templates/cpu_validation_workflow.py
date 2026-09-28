from app.workflows.actions.diagnostics.run_cpu_diagnostic_action import (
    RunCpuDiagnosticAction,
)
from app.workflows.workflow import (
    Workflow,
)


def create_cpu_validation_workflow() -> Workflow:
    return Workflow(
        name="cpu_validation_workflow",
        actions=[
            RunCpuDiagnosticAction(),
        ],
    )