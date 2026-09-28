from app.workflows.execution.execution_record import (
    ExecutionRecord,
)

from app.workflows.execution.execution_status import (
    ExecutionStatus,
)

from app.workflows.execution.file_execution_repository import (
    FileExecutionRepository,
)


def test_save_and_load(
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

    loaded = repository.load(
        record.execution_id
    )

    assert (
        loaded.execution_id
        == record.execution_id
    )

    assert (
        loaded.workflow_name
        == "backup"
    )


def test_exists(
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

    assert repository.exists(
        record.execution_id
    )


def test_delete(
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

    repository.delete(
        record.execution_id
    )

    assert not repository.exists(
        record.execution_id
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

    records = (
        repository.list()
    )

    assert len(
        records
    ) == 2


def test_status_roundtrip(
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

    record.mark_failed(
        "boom"
    )

    repository.save(
        record
    )

    loaded = repository.load(
        record.execution_id
    )

    assert (
        loaded.status
        == ExecutionStatus.FAILED
    )

    assert (
        loaded.error_message
        == "boom"
    )