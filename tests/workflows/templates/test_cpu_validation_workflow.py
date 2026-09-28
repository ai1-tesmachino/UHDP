from app.workflows.templates.cpu_validation_workflow import (
    create_cpu_validation_workflow,
)


def test_cpu_validation_workflow():
    workflow = (
        create_cpu_validation_workflow()
    )

    assert (
        workflow.name
        == "cpu_validation_workflow"
    )

    assert len(
        workflow.actions
    ) == 1