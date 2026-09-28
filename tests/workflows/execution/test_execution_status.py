from app.workflows.execution.execution_status import (
    ExecutionStatus,
)


def test_execution_status_values():
    assert (
        ExecutionStatus.PENDING
        == "pending"
    )

    assert (
        ExecutionStatus.RUNNING
        == "running"
    )

    assert (
        ExecutionStatus.COMPLETED
        == "completed"
    )

    assert (
        ExecutionStatus.FAILED
        == "failed"
    )

    assert (
        ExecutionStatus.STOPPED
        == "stopped"
    )