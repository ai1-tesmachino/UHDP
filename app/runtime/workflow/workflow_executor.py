from __future__ import annotations

from app.runtime.workflow.execution_context import (
    ExecutionContext,
)

from app.runtime.workflow.workflow_engine import (
    WorkflowEngine,
)

from app.runtime.workflow.workflow_result import (
    WorkflowResult,
)


class WorkflowExecutor:

    def __init__(
        self,
        engine: WorkflowEngine | None = None,
    ) -> None:
        self._engine = (
            engine
            or WorkflowEngine()
        )

    async def execute(
        self,
        workflow,
        execution_id: str | None = None,
    ) -> WorkflowResult:

        workflow_id = getattr(
            workflow,
            "workflow_id",
            workflow.name,
        )

        context = ExecutionContext(
            workflow_id=workflow_id,
            execution_id=execution_id,
        )

        try:
            self._engine.execute(
                workflow,
                context=context,
            )

            return WorkflowResult.success_result(
                workflow_id=workflow_id,
                execution_id=context.execution_id,
                started_at=context.started_at,
            )

        except Exception as ex:

            return WorkflowResult.failure_result(
                workflow_id=workflow_id,
                execution_id=context.execution_id,
                started_at=context.started_at,
                error=str(ex),
            )