import pytest

from app.runtime.workflow.execution_service import (
    ExecutionService,
)
from app.runtime.workflow.workflow import (
    Workflow,
)
from app.runtime.workflow.workflow_runner import (
    WorkflowRunner,
)
from app.workflows.execution.execution_status import (
    ExecutionStatus,
)
from app.workflows.execution.file_execution_repository import (
    FileExecutionRepository,
)


class FailingRunner:

    async def run(
        self,
        workflow,
        execution_id=None,
    ):
        raise RuntimeError(
            "test execution failure"
        )


@pytest.mark.asyncio
async def test_execution_failure(
    tmp_path,
):
    repository = FileExecutionRepository(
        tmp_path,
    )

    service = ExecutionService(
        execution_repository=repository,
        runner=FailingRunner(),
    )

    workflow = Workflow(
        name="failing_workflow",
        actions=[],
    )

    with pytest.raises(
        RuntimeError,
        match="test execution failure",
    ):
        await service.execute(
            workflow,
        )

    records = repository.list()

    assert len(records) == 1

    record = records[0]

    assert record.workflow_name == workflow.name
    assert record.status == ExecutionStatus.FAILED
    assert record.error_message == (
        "test execution failure"
    )
    assert record.started_at is not None
    assert record.completed_at is not None