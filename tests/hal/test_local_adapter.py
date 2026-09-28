from app.hal.adapters.local_adapter import (
    LocalAdapter,
)
from app.hal.device_info import DeviceInfo


def test_discover_device():
    adapter = LocalAdapter()

    device = adapter.discover_device()

    assert isinstance(
        device,
        DeviceInfo,
    )

    assert device.device_id
    assert device.hostname
    assert device.operating_system
    assert device.architecture