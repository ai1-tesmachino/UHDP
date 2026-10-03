from app.discovery.device_registry import DeviceRegistry
from app.discovery.models.device import Device


def test_device_registry_register_and_get():

    registry = DeviceRegistry()

    device = Device(
        device_id="device-1",
        device_type="cpu",
        name="CPU",
    )

    registry.register(device)

    result = registry.get("device-1")

    assert result is device


def test_device_registry_register_all():

    registry = DeviceRegistry()

    devices = [
        Device(
            device_id="cpu-1",
            device_type="cpu",
            name="CPU",
        ),
        Device(
            device_id="memory-1",
            device_type="memory",
            name="System Memory",
        ),
    ]

    registry.register_all(devices)

    assert len(registry.all()) == 2


def test_device_registry_clear():

    registry = DeviceRegistry()

    registry.register(
        Device(
            device_id="device-1",
            device_type="cpu",
            name="CPU",
        )
    )

    registry.clear()

    assert registry.all() == []
    assert registry.get("device-1") is None