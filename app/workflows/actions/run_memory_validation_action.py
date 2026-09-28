from app.hal.diagnostics.memory_validation import MemoryValidation
from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class RunMemoryValidationAction(Action):

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        context.set(
            "memory_validation",
            MemoryValidation().validate(),
        )