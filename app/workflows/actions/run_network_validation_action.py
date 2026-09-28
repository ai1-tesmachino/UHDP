from app.hal.diagnostics.network_validation import NetworkValidation
from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class RunNetworkValidationAction(Action):

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        context.set(
            "network_validation",
            NetworkValidation().validate(),
        )