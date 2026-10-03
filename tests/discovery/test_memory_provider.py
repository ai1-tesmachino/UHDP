from app.discovery.providers.memory_provider import MemoryProvider


def test_memory_discovery():

    provider = MemoryProvider()

    result = provider.discover()

    assert len(result.devices) == 1

    device = result.devices[0]

    assert device.device_type == "memory"
    assert device.name == "System Memory"

    assert device.properties["total_bytes"] > 0
    assert device.properties["total_gb"] > 0
    assert device.properties["available_bytes"] >= 0
    assert device.properties["used_bytes"] >= 0
    assert 0 <= device.properties["percent_used"] <= 100