import pytest

from app.workflows.actions.fail_action import (
    FailAction,
)

from app.workflows.exceptions.workflow_failed import (
    WorkflowFailed,
)

from app.workflows.workflow_context import (
    WorkflowContext,
)


def test_fail_action():

    with pytest.raises(
        WorkflowFailed,
    ):
        FailAction(
            "failed",
        ).execute(
            WorkflowContext(),
        )