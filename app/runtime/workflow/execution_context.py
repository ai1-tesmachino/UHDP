from __future__ import annotations

from datetime import UTC
from datetime import datetime
from uuid import uuid4

from app.runtime.workflow.context import WorkflowContext


class ExecutionContext(
    WorkflowContext,
):

    def __init__(
        self,
        workflow_id: str,
        execution_id: str | None = None,
    ) -> None:
        super().__init__()

        self.execution_id = (
            execution_id
            or str(uuid4())
        )

        self.workflow_id = workflow_id

        self.started_at = datetime.now(
            UTC
        )

    def elapsed_seconds(
        self,
    ) -> float:
        return (
            datetime.now(UTC)
            - self.started_at
        ).total_seconds()