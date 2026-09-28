import pytest

from tests.plugins.dummy_plugin import DummyPlugin


@pytest.mark.asyncio
async def test_plugin_initialize_called():

    plugin = DummyPlugin()

    await plugin.initialize()

    assert plugin.initialized is True


@pytest.mark.asyncio
async def test_plugin_shutdown_called():

    plugin = DummyPlugin()

    await plugin.shutdown()

    assert plugin.shutdown_called is True