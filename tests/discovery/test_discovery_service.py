from app.discovery.discovery_service import (
    DiscoveryService,
)


def test_discovery_service_discovers_devices():

    service = DiscoveryService()

    result = service.discover()

    assert len(result.devices) >= 3

    device_types = {
        device.device_type
        for device in result.devices
    }

    assert "cpu" in device_types
    assert "memory" in device_types
    assert "storage" in device_types


def test_discovery_service_registers_devices():

    service = DiscoveryService()

    result = service.discover()

    registered = service.get_devices()

    assert len(registered) == len(
        result.devices
    )


def test_discovery_service_get_device():

    service = DiscoveryService()

    result = service.discover()

    device = result.devices[0]

    found = service.get_device(
        device.device_id,
    )

    assert found is not None
    assert found.device_id == device.device_id