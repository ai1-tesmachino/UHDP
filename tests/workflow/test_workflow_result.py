from app.workflows.workflow_result import (
    WorkflowResult,
)

from app.workflows.workflow_status import (
    WorkflowStatus,
)


def test_success_result():

    result = WorkflowResult(
        WorkflowStatus.SUCCESS,
    )

    assert result.success is True