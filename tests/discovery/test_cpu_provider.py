from app.discovery.providers.cpu_provider import CPUProvider


def test_cpu_discovery():

    provider = CPUProvider()

    result = provider.discover()

    assert len(result.devices) == 1

    device = result.devices[0]

    assert device.device_type == "cpu"

    assert device.properties["logical_cores"] > 0

    assert device.properties["physical_cores"] > 0