from .context import WorkflowContext


class WorkflowEngine:

    def execute(
        self,
        workflow,
        context=None,
    ):
        if hasattr(workflow, "enabled") and not workflow.enabled:
            return

        context = (
            context
            or WorkflowContext()
        )

        for action in workflow.actions:
            action.execute(
                context
            )

        return context