from typing import Any


class WorkflowExecutor:

    def execute(
        self,
        workflow: Any,
        context: Any,
    ) -> Any:

        if hasattr(workflow, "execute"):
            return workflow.execute(
                context,
            )

        if hasattr(workflow, "actions"):
            result = None

            for action in workflow.actions:
                result = action.execute(
                    context,
                )

            return result

        raise TypeError(
            "Workflow does not provide an execute method or actions"
        )