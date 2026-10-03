from typing import Any


class WorkflowRegistry:

    def __init__(self) -> None:
        self._workflows: dict[
            str,
            Any,
        ] = {}

    def register(
        self,
        workflow_id: str,
        workflow: Any,
    ) -> None:
        if workflow_id in self._workflows:
            raise ValueError(
                f"Workflow already registered: {workflow_id}"
            )

        self._workflows[
            workflow_id
        ] = workflow

    def get(
        self,
        workflow_id: str,
    ) -> Any | None:
        return self._workflows.get(
            workflow_id,
        )

    def unregister(
        self,
        workflow_id: str,
    ) -> None:
        self._workflows.pop(
            workflow_id,
            None,
        )

    def list_workflows(self) -> list[str]:
        return list(
            self._workflows.keys()
        )

    def clear(self) -> None:
        self._workflows.clear()

    def __contains__(
        self,
        workflow_id: str,
    ) -> bool:
        return workflow_id in self._workflows