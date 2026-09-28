from __future__ import annotations

from unittest.mock import Mock

from app.runtime.workflow.workflow_service import (
    WorkflowService,
)


def test_workflow_service_save():
    repository = Mock()
    validator = Mock()

    service = WorkflowService(
        workflow_repository=repository,
        validator=validator,
    )

    workflow = object()

    service.save(
        workflow,
    )

    validator.validate.assert_called_once_with(
        workflow,
    )

    repository.save.assert_called_once_with(
        workflow,
    )