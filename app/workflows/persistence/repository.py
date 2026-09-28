from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from app.workflows.workflow import Workflow


class WorkflowRepository(ABC):

    @abstractmethod
    def save(
        self,
        workflow: Workflow,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(
        self,
        name: str,
    ) -> Workflow:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        name: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
    ) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        name: str,
    ) -> bool:
        raise NotImplementedError