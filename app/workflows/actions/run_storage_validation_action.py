from app.hal.diagnostics.storage_validation import StorageValidation
from app.workflows.actions.base import Action
from app.workflows.workflow_context import WorkflowContext


class RunStorageValidationAction(Action):

    def execute(
        self,
        context: WorkflowContext,
    ) -> None:

        context.set(
            "storage_validation",
            StorageValidation().validate(),
        )