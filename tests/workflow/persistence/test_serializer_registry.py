from app.workflows.persistence import (
    SerializerRegistry,
)
from app.workflows.persistence import (
    ActionSerializer,
)


class DummySerializer(
    ActionSerializer
):

    @property
    def action_type(self):
        return "Dummy"

    def serialize(self, action):
        return {}

    def deserialize(self, data):
        return object()


def test_register_serializer():
    registry = SerializerRegistry()

    serializer = DummySerializer()

    registry.register(serializer)

    assert registry.exists("Dummy")


def test_get_serializer():
    registry = SerializerRegistry()

    serializer = DummySerializer()

    registry.register(serializer)

    assert registry.get("Dummy") is serializer