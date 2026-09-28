from app.workflows.execution.audit_entry import (
    AuditEntry,
)

from app.workflows.execution.audit_trail import (
    AuditTrail,
)


def test_add_entry():
    trail = AuditTrail()

    trail.add(
        AuditEntry(
            workflow_name="backup",
            execution_id="1",
            message="started",
        )
    )

    assert len(
        trail.list()
    ) == 1


def test_filter_by_execution():
    trail = AuditTrail()

    trail.add(
        AuditEntry(
            workflow_name="backup",
            execution_id="1",
            message="started",
        )
    )

    trail.add(
        AuditEntry(
            workflow_name="backup",
            execution_id="2",
            message="started",
        )
    )

    entries = (
        trail.by_execution(
            "1"
        )
    )

    assert len(
        entries
    ) == 1


def test_filter_by_workflow():
    trail = AuditTrail()

    trail.add(
        AuditEntry(
            workflow_name="backup",
            execution_id="1",
            message="started",
        )
    )

    trail.add(
        AuditEntry(
            workflow_name="cleanup",
            execution_id="2",
            message="started",
        )
    )

    entries = (
        trail.by_workflow(
            "backup"
        )
    )

    assert len(
        entries
    ) == 1


def test_clear():
    trail = AuditTrail()

    trail.add(
        AuditEntry(
            workflow_name="backup",
            execution_id="1",
            message="started",
        )
    )

    trail.clear()

    assert (
        trail.list()
        == []
    )