from app.workflows.execution.audit_entry import (
    AuditEntry,
)


def test_audit_entry_defaults():
    entry = AuditEntry(
        workflow_name="backup",
        execution_id="1",
        message="started",
    )

    assert (
        entry.workflow_name
        == "backup"
    )

    assert (
        entry.execution_id
        == "1"
    )

    assert (
        entry.message
        == "started"
    )

    assert (
        entry.timestamp
        is not None
    )