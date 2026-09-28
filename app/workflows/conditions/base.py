from abc import ABC
from abc import abstractmethod

from app.workflows.workflow_context import WorkflowContext


class Condition(ABC):

    @abstractmethod
    def evaluate(
        self,
        context: WorkflowContext,
    ) -> bool:
        pass 