from app.workflows.templates.network_validation_workflow import (
    create_network_validation_workflow,
)


def test_network_validation_workflow():
    workflow = (
        create_network_validation_workflow()
    )

    assert (
        workflow.name
        == "network_validation_workflow"
    )

    assert len(
        workflow.actions
    ) == 1