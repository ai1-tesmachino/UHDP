import pytest
from app.runtime.workflow.execution_service import (    ExecutionService,)
from app.workflows.execution.file_execution_repository import FileExecutionRepository
from app.runtime.workflow.workflow_runner import WorkflowRunner
from app.workflows.workflow import Workflow
from app.workflows.execution.execution_status import (    ExecutionStatus,)




@pytest.mark.asyncio
async def test_execution_service(
    tmp_path,
):
    repository = FileExecutionRepository(
        tmp_path,
    )

    service = ExecutionService(
        execution_repository=repository,
        runner=WorkflowRunner(),
    )

    workflow = Workflow(
        name="service_workflow",
        actions=[],
    )

    result = await service.execute(
        workflow,
    )

    assert result.success is True

    record = repository.load(
        result.execution_id,
    )

    assert record.execution_id == result.execution_id
    assert record.workflow_name == workflow.name
    assert record.status == ExecutionStatus.COMPLETED