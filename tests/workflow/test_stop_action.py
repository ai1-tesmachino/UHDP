from app.workflows.actions.stop_action import (
    StopAction,
)
from app.workflows.workflow_context import (
    WorkflowContext,
)


def test_stop_action():

    action = StopAction()

    try:
        action.execute(
            WorkflowContext(),
        )
    except Exception:
        return

    assert False