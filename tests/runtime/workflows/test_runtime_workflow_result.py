from datetime import UTC
from datetime import datetime

from app.runtime.workflow.workflow_result import (
    WorkflowResult,
)


def test_success_result():

    started_at = datetime.now(UTC)

    result = WorkflowResult.success_result(
        workflow_id="workflow-1",
        execution_id="execution-1",
        started_at=started_at,
    )

    assert result.workflow_id == "workflow-1"
    assert result.execution_id == "execution-1"
    assert result.success is True
    assert result.error is None
    assert result.finished_at >= started_at


def test_failure_result():

    started_at = datetime.now(UTC)

    result = WorkflowResult.failure_result(
        workflow_id="workflow-1",
        execution_id="execution-1",
        started_at=started_at,
        error="execution failed",
    )

    assert result.workflow_id == "workflow-1"
    assert result.execution_id == "execution-1"
    assert result.success is False
    assert result.error == "execution failed"