import pytest

from app.runtime.workflow.actions import (
    SetVariableAction,
)
from app.runtime.workflow.workflow import Workflow
from app.runtime.workflow.workflow_executor import WorkflowExecutor
from app.runtime.workflow.workflow_runner import WorkflowRunner


@pytest.mark.asyncio
async def test_workflow_executor_executes_workflow():

    workflow = Workflow(
        name="test_workflow",
        actions=[
            SetVariableAction(
                "value",
                42,
            ),
        ],
    )

    executor = WorkflowExecutor()

    result = await executor.execute(
        workflow,
    )

    assert result.success is True
    assert result.workflow_id == workflow.workflow_id
    assert result.execution_id
    assert result.error is None
    assert result.finished_at >= result.started_at


@pytest.mark.asyncio
async def test_workflow_runner_executes_workflow():

    workflow = Workflow(
        name="test_workflow",
        actions=[],
    )

    runner = WorkflowRunner()

    result = await runner.run(
        workflow,
    )

    assert result.success is True
    assert result.workflow_id == workflow.workflow_id
    assert result.execution_id