from app.discovery.providers.storage_provider import StorageProvider


def test_storage_discovery():

    provider = StorageProvider()

    result = provider.discover()

    assert len(result.devices) >= 1

    for device in result.devices:

        assert device.device_type == "storage"

        assert device.name

        assert device.properties["device"]
        assert device.properties["mountpoint"]
        assert device.properties["filesystem"]

        assert device.properties["total_bytes"] > 0
        assert device.properties["free_bytes"] >= 0
        assert device.properties["used_bytes"] >= 0

        assert 0 <= device.properties["percent_used"] <= 100
        assert device.properties["total_gb"] > 0