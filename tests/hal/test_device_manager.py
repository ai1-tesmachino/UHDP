from app.hal.adapters.base_adapter import (
    BaseAdapter,
)


from app.hal.device_info import DeviceInfo
from app.hal.device_manager import (
    DeviceManager,
)


class FakeAdapter(BaseAdapter):

    def discover_device(
        self,
    ) -> DeviceInfo:
        return DeviceInfo(
            device_id="device-1",
            hostname="TEST-PC",
            operating_system="Windows",
            architecture="AMD64",
        )


def test_get_device():
    manager = DeviceManager(
        FakeAdapter(),
    )

    device = manager.get_device()

    assert device.device_id == "device-1"
    assert device.hostname == "TEST-PC"
    assert device.operating_system == "Windows"
    assert device.architecture == "AMD64"