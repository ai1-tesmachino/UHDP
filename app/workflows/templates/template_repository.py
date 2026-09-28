from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from app.workflows.templates.template import (
    WorkflowTemplate,
)


class TemplateRepository(
    ABC,
):

    @abstractmethod
    def save(
        self,
        template: WorkflowTemplate,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(
        self,
        name: str,
    ) -> WorkflowTemplate:
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