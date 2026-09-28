import pytest

from app.runtime.workflow.actions import (
    PrintAction,
)
from app.workflows.workflow import Workflow
from app.runtime.workflow.workflow_runner import (
    WorkflowRunner,
)


@pytest.mark.asyncio
async def test_runner_executes_workflow():

    workflow = Workflow(
        name="runner-test",
        actions=[
            PrintAction(
                "hello",
            ),
        ],
    )

    runner = WorkflowRunner()

    result = await runner.run(
        workflow,
    )

    assert result.success is True
    assert (
        result.workflow_id
        == workflow.workflow_id
    )