from app.runtime.workflow.actions import (
    SetVariableAction,
    PrintVariableAction,
)

from app.workflows.workflow import Workflow
from app.runtime.workflow.workflow_engine import WorkflowEngine


workflow = Workflow(
    name="context-demo",
    actions=[
        SetVariableAction(
            "device",
            "Server-01",
        ),

        PrintVariableAction(
            "device",
        ),
    ],
)

WorkflowEngine().execute(
    workflow
)