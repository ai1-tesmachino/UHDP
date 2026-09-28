from app.workflows.execution.execution_query import (
    ExecutionQuery,
)

from app.workflows.execution.execution_status import (
    ExecutionStatus,
)


def test_query_defaults():
    query = ExecutionQuery()

    assert (
        query.workflow_name
        is None
    )

    assert (
        query.status
        is None
    )


def test_query_values():
    query = ExecutionQuery(
        workflow_name="backup",
        status=ExecutionStatus.FAILED,
    )

    assert (
        query.workflow_name
        == "backup"
    )

    assert (
        query.status
        == ExecutionStatus.FAILED
    )