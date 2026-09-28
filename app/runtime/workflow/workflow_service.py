from __future__ import annotations


class WorkflowService:
    def __init__(
        self,
        workflow_repository,
        validator=None,
    ) -> None:
        self._repository = workflow_repository
        self._validator = validator

    def save(
        self,
        workflow,
    ) -> None:
        if self._validator is not None:
            self._validator.validate(
                workflow,
            )

        self._repository.save(
            workflow,
        )

    def get(
        self,
        workflow_id: str,
    ):
        return self._repository.load(
            workflow_id,
        )

    def delete(
        self,
        workflow_id: str,
    ) -> None:
        self._repository.delete(
            workflow_id,
        )

    def list(
        self,
    ):
        return self._repository.list()