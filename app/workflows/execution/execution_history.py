from __future__ import annotations

from app.workflows.execution.execution_record import (
    ExecutionRecord,
)

from app.workflows.execution.execution_repository import (
    ExecutionRepository,
)

from app.workflows.execution.execution_query import (
    ExecutionQuery,
)


class ExecutionHistory:

    def __init__(
        self,
        repository: ExecutionRepository,
    ) -> None:
        self._repository = (
            repository
        )

    def get(
        self,
        execution_id: str,
    ) -> ExecutionRecord:
        return self._repository.load(
            execution_id
        )

    def list(
        self,
    ) -> list[ExecutionRecord]:
        return self._repository.list()

    def query(
        self,
        query: ExecutionQuery,
    ) -> list[ExecutionRecord]:
        records = (
            self._repository.list()
        )

        if (
            query.workflow_name
            is not None
        ):
            records = [
                record
                for record in records
                if record.workflow_name
                == query.workflow_name
            ]

        if (
            query.status
            is not None
        ):
            records = [
                record
                for record in records
                if record.status
                == query.status
            ]

        return records