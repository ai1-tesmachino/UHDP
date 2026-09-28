from app.workflows.templates.builtins import (
    get_builtin_templates,
)


def test_builtin_templates():
    templates = (
        get_builtin_templates()
    )

    assert isinstance(
        templates,
        list,
    )