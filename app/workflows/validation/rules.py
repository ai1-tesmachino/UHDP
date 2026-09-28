from typing import Protocol

from app.workflows.validation.validation_error import (
    ValidationError,
)


class ValidationRule(Protocol):

    def validate(
        self,
        workflow: object,
    ) -> list[ValidationError]:
        ...


class WorkflowNameRule:

    def validate(
        self,
        workflow: object,
    ) -> list[ValidationError]:
        name = getattr(
            workflow,
            "name",
            "",
        )

        if isinstance(name, str) and name.strip():
            return []

        return [
            ValidationError(
                code="missing_workflow_name",
                message="Workflow name is required.",
                path="name",
            ),
        ]


class WorkflowActionRule:

    def validate(
        self,
        workflow: object,
    ) -> list[ValidationError]:
        actions = getattr(
            workflow,
            "actions",
            None,
        )

        if actions:
            return []

        return [
            ValidationError(
                code="missing_actions",
                message="Workflow must contain at least one action.",
                path="actions",
            ),
        ]