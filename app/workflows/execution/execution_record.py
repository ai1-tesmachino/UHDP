from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from datetime import UTC
from datetime import datetime

from uuid import uuid4

from app.workflows.execution.execution_status import (
    ExecutionStatus,
)


@dataclass(
    slots=True,
)
class ExecutionRecord:
    workflow_name: str

    execution_id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    status: ExecutionStatus = (
        ExecutionStatus.PENDING
    )

    started_at: datetime | None = None

    completed_at: datetime | None = None

    error_message: str | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            UTC
        )
    )

    def mark_running(
        self,
    ) -> None:
        self.status = (
            ExecutionStatus.RUNNING
        )

        self.started_at = datetime.now(
            UTC
        )

    def mark_completed(
        self,
    ) -> None:
        self.status = (
            ExecutionStatus.COMPLETED
        )

        self.completed_at = datetime.now(
            UTC
        )

    def mark_failed(
        self,
        message: str,
    ) -> None:
        self.status = (
            ExecutionStatus.FAILED
        )

        self.error_message = message

        self.completed_at = datetime.now(
            UTC
        )

    def mark_stopped(
        self,
    ) -> None:
        self.status = (
            ExecutionStatus.STOPPED
        )

        self.completed_at = datetime.now(
            UTC
        )