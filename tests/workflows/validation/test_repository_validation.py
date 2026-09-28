import pytest

from app.workflows.persistence.file_repository import (
    FileWorkflowRepository,
)

from app.workflows.validation.validation_exception import (
    ValidationException,
)


class InvalidWorkflow:

    name = ""
    actions = []


def test_repository_rejects_invalid_workflow(
    tmp_path,
):
    repository = FileWorkflowRepository(
        tmp_path
    )

    workflow = InvalidWorkflow()

    with pytest.raises(
        ValidationException,
    ):
        repository.save(
            workflow
        )