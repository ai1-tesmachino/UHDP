# app/workflows/actions/base.py

from abc import ABC
from abc import abstractmethod

from app.workflows.workflow_context import WorkflowContext


class Action(ABC):

    @abstractmethod
    def execute(
        self,
        context: WorkflowContext,
    ) -> None:
        raise NotImplementedError