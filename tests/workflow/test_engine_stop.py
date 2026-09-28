from app.workflows.actions.stop_action import (
    StopAction,
)

from app.workflows.workflow import Workflow

from app.workflows.workflow_engine import (
    WorkflowEngine,
)

from app.workflows.workflow_status import (
    WorkflowStatus,
)


def test_engine_stopped():

    workflow = Workflow(
        name="test",
        actions=[
            StopAction(),
        ],
    )

    engine = WorkflowEngine()

    result = engine.execute(
        workflow,
    )

    assert (
        result.status
        == WorkflowStatus.STOPPED
    )