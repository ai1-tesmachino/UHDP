from app.workflows.templates.storage_validation_workflow import (
    create_storage_validation_workflow,
)


def test_storage_validation_workflow():
    workflow = (
        create_storage_validation_workflow()
    )

    assert (
        workflow.name
        == "storage_validation_workflow"
    )

    assert len(
        workflow.actions
    ) == 1