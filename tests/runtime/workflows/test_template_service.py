from __future__ import annotations

from unittest.mock import Mock

from app.runtime.workflow.template_service import (
    TemplateService,
)


def test_template_service_save():
    repository = Mock()

    service = TemplateService(
        template_repository=repository,
    )

    template = object()

    service.save(
        template,
    )

    repository.save.assert_called_once_with(
        template,
    )