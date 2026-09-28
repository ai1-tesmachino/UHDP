from app.workflows.persistence.serializer import (
    WorkflowSerializer,
)

from app.workflows.workflow import Workflow


def test_serialize_workflow():

    serializer = WorkflowSerializer()

    workflow = Workflow(
        name="sample",
        actions=[],
    )

    data = serializer.serialize(
        workflow,
    )

    assert data["name"] == "sample"


def test_deserialize_workflow():

    serializer = WorkflowSerializer()

    workflow = serializer.deserialize(
        {
            "name": "sample",
        }
    )

    assert workflow.name == "sample"