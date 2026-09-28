from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime


@dataclass(slots=True)
class WorkflowResult:
    workflow_id: str
    execution_id: str
    success: bool
    started_at: datetime
    finished_at: datetime
    error: str | None = None

    @property
    def duration_seconds(
        self,
    ) -> float:
        return (
            self.finished_at
            - self.started_at
        ).total_seconds()

    @classmethod
    def success_result(
        cls,
        workflow_id: str,
        execution_id: str,
        started_at: datetime,
    ) -> "WorkflowResult":
        return cls(
            workflow_id=workflow_id,
            execution_id=execution_id,
            success=True,
            started_at=started_at,
            finished_at=datetime.now(
                UTC,
            ),
        )

    @classmethod
    def failure_result(
        cls,
        workflow_id: str,
        execution_id: str,
        started_at: datetime,
        error: str,
    ) -> "WorkflowResult":
        return cls(
            workflow_id=workflow_id,
            execution_id=execution_id,
            success=False,
            started_at=started_at,
            finished_at=datetime.now(
                UTC,
            ),
            error=error,
        )