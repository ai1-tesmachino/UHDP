from app.workflows.validation.rules import (
    WorkflowActionRule,
    WorkflowNameRule,
)
from app.workflows.validation.validator import WorkflowValidator

from app.workflows.validation.validator import (
    create_default_validator,
)

class FakeWorkflow:

    def __init__(
        self,
        name: str = "",
        actions: list[object] | None = None,
    ) -> None:
        self.name = name
        self.actions = actions or []

def test_default_validator():
    validator = create_default_validator()

    assert validator is not None
    
def test_validator_with_real_rules():
    validator = WorkflowValidator(
        [
            WorkflowNameRule(),
            WorkflowActionRule(),
        ],
    )

    workflow = FakeWorkflow()

    result = validator.validate(workflow)

    assert result.is_valid is False
    assert len(result.errors) == 2