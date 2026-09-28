from app.workflows.workflow import Workflow

from app.workflows.actions.print_action import (
    PrintAction,
)

from app.workflows.persistence.default_serializers import (
    create_default_registry,
)

from app.workflows.persistence.serializer import (
    WorkflowSerializer,
)


def test_serialize_workflow():
  
    workflow = Workflow(
    name="test",
    actions=[
        PrintAction("hello")
    ],
    )

    serializer = WorkflowSerializer(
        create_default_registry()
    )

    data = serializer.serialize(
        workflow
    )

    assert data["name"] == "test"
    assert len(data["actions"]) == 1
    assert (
        data["actions"][0]["type"]
        == "PrintAction"
    )


def test_deserialize_workflow():
    serializer = WorkflowSerializer(
        create_default_registry()
    )

    workflow = serializer.deserialize(
        {
            "name": "test",
            "actions": [
                {
                    "type": "PrintAction",
                    "config": {
                        "message": "hello"
                    },
                }
            ],
        }
    )

    assert workflow.name == "test"
    assert len(workflow.actions) == 1