from .workflow import Workflow


class WorkflowRegistry:
    def __init__(self):
        self._workflows = {}

    def register(
        self,
        workflow: Workflow,
    ):
        self._workflows[
            workflow.workflow_id
        ] = workflow

    def get(
        self,
        workflow_id: str,
    ):
        return self._workflows.get(
            workflow_id
        )

    def all(self):
        return list(
            self._workflows.values()
        )

    def unregister(
        self,
        workflow_id: str,
    ):
        self._workflows.pop(
            workflow_id,
            None,
        )