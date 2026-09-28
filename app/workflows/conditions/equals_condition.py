from app.workflows.conditions.base import Condition
from app.workflows.workflow_context import WorkflowContext


class EqualsCondition(Condition):

    def __init__(
        self,
        variable_name: str,
        expected_value,
    ) -> None:
        self.variable_name = variable_name
        self.expected_value = expected_value

    def evaluate(
        self,
        context: WorkflowContext,
    ) -> bool:
        return (
            context.get(self.variable_name)
            == self.expected_value
        )