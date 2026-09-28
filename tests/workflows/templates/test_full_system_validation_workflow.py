from app.workflows.templates.full_system_validation_workflow import (
    create_full_system_validation_workflow,
)


def test_full_system_validation_workflow():
    workflow = (
        create_full_system_validation_workflow()
    )

    assert (
        workflow.name
        == "full_system_validation_workflow"
    )

    assert len(
        workflow.actions
    ) == 4

    