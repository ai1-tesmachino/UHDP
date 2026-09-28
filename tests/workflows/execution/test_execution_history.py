from app.workflows.execution.execution_record import (
    ExecutionRecord,
)

from app.workflows.execution.execution_history import (
    ExecutionHistory,
)

from app.workflows.execution.execution_query import (
    ExecutionQuery,
)

from app.workflows.execution.execution_status import (
    ExecutionStatus,
)

from app.workflows.execution.file_execution_repository import (
    FileExecutionRepository,
)


def test_list(
    tmp_path,
):
    repository = (
        FileExecutionRepository(
            tmp_path
        )
    )

    repository.save(
        ExecutionRecord(
            workflow_name="a"
        )
    )

    repository.save(
        ExecutionRecord(
            workflow_name="b"
        )
    )

    history = ExecutionHistory(
        repository
    )

    assert len(
        history.list()
    ) == 2


def test_get(
    tmp_path,
):
    repository = (
        FileExecutionRepository(
            tmp_path
        )
    )

    record = ExecutionRecord(
        workflow_name="backup"
    )

    repository.save(
        record
    )

    history = ExecutionHistory(
        repository
    )

    loaded = history.get(
        record.execution_id
    )

    assert (
        loaded.execution_id
        == record.execution_id
    )


def test_query_by_workflow(
    tmp_path,
):
    repository = (
        FileExecutionRepository(
            tmp_path
        )
    )

    repository.save(
        ExecutionRecord(
            workflow_name="backup"
        )
    )

    repository.save(
        ExecutionRecord(
            workflow_name="cleanup"
        )
    )

    history = ExecutionHistory(
        repository
    )

    records = history.query(
        ExecutionQuery(
            workflow_name="backup"
        )
    )

    assert len(
        records
    ) == 1

    assert (
        records[0].workflow_name
        == "backup"
    )


def test_query_by_status(
    tmp_path,
):
    repository = (
        FileExecutionRepository(
            tmp_path
        )
    )

    failed = ExecutionRecord(
        workflow_name="backup"
    )

    failed.mark_failed(
        "boom"
    )

    repository.save(
        failed
    )

    completed = (
        ExecutionRecord(
            workflow_name="backup"
        )
    )

    completed.mark_completed()

    repository.save(
        completed
    )

    history = ExecutionHistory(
        repository
    )

    records = history.query(
        ExecutionQuery(
            status=ExecutionStatus.FAILED
        )
    )

    assert len(
        records
    ) == 1

    assert (
        records[0].status
        == ExecutionStatus.FAILED
    )


def test_query_by_workflow_and_status(
    tmp_path,
):
    repository = (
        FileExecutionRepository(
            tmp_path
        )
    )

    failed = ExecutionRecord(
        workflow_name="backup"
    )

    failed.mark_failed(
        "boom"
    )

    repository.save(
        failed
    )

    completed = (
        ExecutionRecord(
            workflow_name="backup"
        )
    )

    completed.mark_completed()

    repository.save(
        completed
    )

    history = ExecutionHistory(
        repository
    )

    records = history.query(
        ExecutionQuery(
            workflow_name="backup",
            status=ExecutionStatus.FAILED,
        )
    )

    assert len(
        records
    ) == 1

    assert (
        records[0].status
        == ExecutionStatus.FAILED
    )