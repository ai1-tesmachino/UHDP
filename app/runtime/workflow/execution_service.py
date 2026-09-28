from __future__ import annotations

from app.workflows.execution.audit_entry import (
    AuditEntry,
)

from app.workflows.execution.execution_record import (
    ExecutionRecord,
)


class ExecutionService:

    def __init__(
        self,
        execution_repository,
        runner,
        audit_trail=None,
    ) -> None:
        self._repository = execution_repository
        self._runner = runner
        self._audit_trail = audit_trail

    async def execute(
        self,
        workflow,
    ):
        record = ExecutionRecord(
            workflow_name=workflow.name,
        )

        self._repository.save(
            record
        )

        record.mark_running()

        self._repository.save(
            record
        )

        self._audit(
            workflow=workflow,
            execution_id=record.execution_id,
            message="Workflow execution started",
        )

        try:
            result = await self._runner.run(
                workflow,
                execution_id=record.execution_id,
            )

            if result.success:
                record.mark_completed()

                self._repository.save(
                    record
                )

                self._audit(
                    workflow=workflow,
                    execution_id=record.execution_id,
                    message="Workflow execution completed",
                )

            else:
                record.mark_failed(
                    result.error
                    or "Workflow execution failed"
                )

                self._repository.save(
                    record
                )

                self._audit(
                    workflow=workflow,
                    execution_id=record.execution_id,
                    message="Workflow execution failed",
                )

            return result

        except Exception as ex:
            record.mark_failed(
                str(ex)
            )

            self._repository.save(
                record
            )

            self._audit(
                workflow=workflow,
                execution_id=record.execution_id,
                message="Workflow execution failed",
            )

            raise

    def get(
        self,
        execution_id: str,
    ):
        return self._repository.load(
            execution_id
        )

    def list(
        self,
    ):
        return self._repository.list()

    def _audit(
        self,
        workflow,
        execution_id: str,
        message: str,
    ) -> None:
        if self._audit_trail is None:
            return

        self._audit_trail.add(
            AuditEntry(
                workflow_name=workflow.name,
                execution_id=execution_id,
                message=message,
            )
        )