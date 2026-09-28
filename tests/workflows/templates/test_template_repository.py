import pytest

from app.workflows.templates.template_repository import (
    TemplateRepository,
)


def test_repository_is_abstract():
    with pytest.raises(
        TypeError
    ):
        TemplateRepository()