from __future__ import annotations

from dataclasses import dataclass

from app.workflows.execution.execution_status import (
    ExecutionStatus,
)


@dataclass(
    slots=True,
)
class ExecutionQuery:
    workflow_name: str | None = None

    status: ExecutionStatus | None = None