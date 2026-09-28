from __future__ import annotations

from app.runtime.workflow.workflow_executor import (
    WorkflowExecutor,
)


class WorkflowRunner:

    def __init__(
        self,
        executor: WorkflowExecutor | None = None,
    ) -> None:
        self._executor = (
            executor
            or WorkflowExecutor()
        )

    async def run(
        self,
        workflow,
        execution_id: str | None = None,
    ):
        return await self._executor.execute(
            workflow,
            execution_id=execution_id,
        )