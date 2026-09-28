from app.workflows.execution.execution_record import (
    ExecutionRecord,
)

from app.workflows.execution.execution_status import (
    ExecutionStatus,
)


def test_record_defaults():
    record = ExecutionRecord(
        workflow_name="test"
    )

    assert record.workflow_name == "test"

    assert (
        record.status
        == ExecutionStatus.PENDING
    )

    assert record.execution_id


def test_mark_running():
    record = ExecutionRecord(
        workflow_name="test"
    )

    record.mark_running()

    assert (
        record.status
        == ExecutionStatus.RUNNING
    )

    assert (
        record.started_at
        is not None
    )


def test_mark_completed():
    record = ExecutionRecord(
        workflow_name="test"
    )

    record.mark_completed()

    assert (
        record.status
        == ExecutionStatus.COMPLETED
    )

    assert (
        record.completed_at
        is not None
    )


def test_mark_failed():
    record = ExecutionRecord(
        workflow_name="test"
    )

    record.mark_failed(
        "boom"
    )

    assert (
        record.status
        == ExecutionStatus.FAILED
    )

    assert (
        record.error_message
        == "boom"
    )

    assert (
        record.completed_at
        is not None
    )


def test_mark_stopped():
    record = ExecutionRecord(
        workflow_name="test"
    )

    record.mark_stopped()

    assert (
        record.status
        == ExecutionStatus.STOPPED
    )

    assert (
        record.completed_at
        is not None
    )