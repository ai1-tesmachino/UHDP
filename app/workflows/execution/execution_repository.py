from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from app.workflows.execution.execution_record import (
    ExecutionRecord,
)


class ExecutionRepository(
    ABC,
):

    @abstractmethod
    def save(
        self,
        record: ExecutionRecord,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(
        self,
        execution_id: str,
    ) -> ExecutionRecord:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        execution_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
    ) -> list[ExecutionRecord]:
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        execution_id: str,
    ) -> bool:
        raise NotImplementedError