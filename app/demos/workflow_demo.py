from app.runtime.workflow.actions import PrintAction
from app.workflows.workflow import Workflow
from app.runtime.workflow.workflow_engine import WorkflowEngine


workflow = Workflow(
    name="demo-workflow",
    actions=[
        PrintAction(
            "STEP 1"
        ),
        PrintAction(
            "STEP 2"
        ),
        PrintAction(
            "STEP 3"
        ),
    ],
)

WorkflowEngine().execute(
    workflow
)