from app.workflows.actions.diagnostics.run_network_diagnostic_action import (
    RunNetworkDiagnosticAction,
)
from app.workflows.workflow import (
    Workflow,
)


def create_network_validation_workflow() -> Workflow:
    return Workflow(
        name="network_validation_workflow",
        actions=[
            RunNetworkDiagnosticAction(),
        ],
    )