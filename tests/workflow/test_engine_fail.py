from app.workflows.actions.fail_action import (
    FailAction,
)

from app.workflows.workflow import Workflow

from app.workflows.workflow_engine import (
    WorkflowEngine,
)

from app.workflows.workflow_status import (
    WorkflowStatus,
)


def test_engine_failed():

    workflow = Workflow(
        name="test",
        actions=[
            FailAction(
                "error",
            ),
        ],
    )

    engine = WorkflowEngine()

    result = engine.execute(
        workflow,
    )

    assert (
        result.status
        == WorkflowStatus.FAILED
    )