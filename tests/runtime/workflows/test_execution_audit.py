import pytest

from app.runtime.workflow.execution_service import (
    ExecutionService,
)

from app.workflows.workflow import Workflow

from app.runtime.workflow.workflow_runner import (
    WorkflowRunner,
)

from app.workflows.execution.audit_trail import (
    AuditTrail,
)

from app.workflows.execution.execution_status import (
    ExecutionStatus,
)

from app.workflows.execution.file_execution_repository import (
    FileExecutionRepository,
)


@pytest.mark.asyncio
async def test_execution_audit_success(
    tmp_path,
):
    repository = FileExecutionRepository(
        tmp_path,
    )

    audit_trail = AuditTrail()

    service = ExecutionService(
        execution_repository=repository,
        runner=WorkflowRunner(),
        audit_trail=audit_trail,
    )

    workflow = Workflow(
        name="audit_success_workflow",
        actions=[],
    )

    result = await service.execute(
        workflow,
    )

    assert result.success is True

    entries = audit_trail.by_execution(
        result.execution_id,
    )

    assert len(entries) == 2

    assert entries[0].workflow_name == (
        workflow.name
    )

    assert entries[0].execution_id == (
        result.execution_id
    )

    assert entries[0].message == (
        "Workflow execution started"
    )

    assert entries[1].message == (
        "Workflow execution completed"
    )


@pytest.mark.asyncio
async def test_execution_audit_failure(
    tmp_path,
):
    repository = FileExecutionRepository(
        tmp_path,
    )

    audit_trail = AuditTrail()

    class FailingRunner:

        async def run(
            self,
            workflow,
            execution_id=None,
        ):
            raise RuntimeError(
                "audit failure"
            )

    service = ExecutionService(
        execution_repository=repository,
        runner=FailingRunner(),
        audit_trail=audit_trail,
    )

    workflow = Workflow(
        name="audit_failure_workflow",
        actions=[],
    )

    with pytest.raises(
        RuntimeError,
        match="audit failure",
    ):
        await service.execute(
            workflow,
        )

    record = repository.list()[0]

    assert record.status == (
        ExecutionStatus.FAILED
    )

    entries = audit_trail.by_execution(
        record.execution_id,
    )

    assert len(entries) == 2

    assert entries[0].message == (
        "Workflow execution started"
    )

    assert entries[1].message == (
        "Workflow execution failed"
    )