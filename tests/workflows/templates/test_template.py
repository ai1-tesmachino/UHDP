from app.workflows.workflow import (
    Workflow,
)

from app.workflows.templates.template import (
    WorkflowTemplate,
)


def test_template_properties():
    workflow = Workflow(
        name="workflow",
        actions=[],
    )

    template = WorkflowTemplate(
        name="template",
        description="desc",
        workflow=workflow,
    )

    assert (
        template.name
        == "template"
    )

    assert (
        template.description
        == "desc"
    )

    assert (
        template.workflow
        is workflow
    )