from collections.abc import Iterable

from app.workflows.validation.rules import (
    ValidationRule,
    WorkflowActionRule,
    WorkflowNameRule,
)

from app.workflows.validation.validation_result import (
    ValidationResult,
)


class WorkflowValidator:

    def __init__(
        self,
        rules: Iterable[ValidationRule] | None = None,
    ) -> None:
        self._rules = list(
            rules or []
        )

    def validate(
        self,
        workflow: object,
    ) -> ValidationResult:
        result = ValidationResult()

        for rule in self._rules:
            result.extend(
                rule.validate(
                    workflow
                )
            )

        return result


def create_default_validator() -> WorkflowValidator:
    return WorkflowValidator(
        [
            WorkflowNameRule(),
            WorkflowActionRule(),
        ]
    )