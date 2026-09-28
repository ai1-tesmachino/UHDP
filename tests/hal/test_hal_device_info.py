from app.hal.device_info import (
    DeviceInfo,
)


def test_device_info_creation():
    device = DeviceInfo(
        device_id="local",
        hostname="TEST-PC",
        operating_system="Windows",
        architecture="AMD64",
    )

    assert device.device_id == "local"
    assert device.hostname == "TEST-PC"
    assert device.operating_system == "Windows"
    assert device.architecture == "AMD64"