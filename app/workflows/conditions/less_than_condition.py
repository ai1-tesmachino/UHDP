from app.workflows.conditions.base import Condition
from app.workflows.workflow_context import WorkflowContext


class LessThanCondition(Condition):

    def __init__(
        self,
        variable_name: str,
        value,
    ) -> None:
        self.variable_name = variable_name
        self.value = value

    def evaluate(
        self,
        context: WorkflowContext,
    ) -> bool:
        return (
            context.get(self.variable_name)
            < self.value
        )