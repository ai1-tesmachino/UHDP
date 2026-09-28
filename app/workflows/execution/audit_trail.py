from __future__ import annotations

from app.workflows.execution.audit_entry import (
    AuditEntry,
)


class AuditTrail:

    def __init__(
        self,
    ) -> None:
        self._entries: list[
            AuditEntry
        ] = []

    def add(
        self,
        entry: AuditEntry,
    ) -> None:
        self._entries.append(
            entry
        )

    def list(
        self,
    ) -> list[AuditEntry]:
        return list(
            self._entries
        )

    def by_execution(
        self,
        execution_id: str,
    ) -> list[AuditEntry]:
        return [
            entry
            for entry in self._entries
            if entry.execution_id
            == execution_id
        ]

    def by_workflow(
        self,
        workflow_name: str,
    ) -> list[AuditEntry]:
        return [
            entry
            for entry in self._entries
            if entry.workflow_name
            == workflow_name
        ]

    def clear(
        self,
    ) -> None:
        self._entries.clear()