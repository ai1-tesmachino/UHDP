from app.workflows.templates.memory_validation_workflow import (
    create_memory_validation_workflow,
)


def test_memory_validation_workflow():
    workflow = (
        create_memory_validation_workflow()
    )

    assert (
        workflow.name
        == "memory_validation_workflow"
    )

    assert len(
        workflow.actions
    ) == 1