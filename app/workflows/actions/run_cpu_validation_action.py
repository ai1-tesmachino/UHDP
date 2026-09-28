from app.hal.diagnostics.cpu_validation import CpuValidation
from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class RunCpuValidationAction(Action):

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        context.set(
            "cpu_validation",
            CpuValidation().validate(),
        )