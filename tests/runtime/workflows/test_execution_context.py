from app.runtime.workflow.execution_context import (
    ExecutionContext,
)


def test_execution_context_creates_execution_id():

    context = ExecutionContext(
        workflow_id="workflow-1",
    )

    assert context.execution_id
    assert context.workflow_id == "workflow-1"
    assert context.started_at is not None


def test_execution_context_stores_variables():

    context = ExecutionContext(
        workflow_id="workflow-1",
    )

    context.set(
        "name",
        "UHDP",
    )

    assert context.get("name") == "UHDP"
    assert context.get("missing") is None
    assert context.get(
        "missing",
        "default",
    ) == "default"


def test_execution_context_elapsed_time():

    context = ExecutionContext(
        workflow_id="workflow-1",
    )

    assert context.elapsed_seconds() >= 0