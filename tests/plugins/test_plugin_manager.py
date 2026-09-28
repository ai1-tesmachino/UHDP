import pytest

from app.plugins.manager import PluginManager
from app.plugins.registry import PluginRegistry

from tests.plugins.dummy_plugin import DummyPlugin


class FakeLoader:
    def load(
        self,
        module_path: str,
    ):
        return DummyPlugin()


class FakeRuntime:
    pass


@pytest.mark.asyncio
async def test_manager_load_calls_initialize():

    manager = PluginManager(
        registry=PluginRegistry(),
        loader=FakeLoader(),
        runtime=FakeRuntime(),
    )

    plugin = await manager.load(
        "dummy.path"
    )

    assert plugin.initialized is True


@pytest.mark.asyncio
async def test_manager_shutdown_calls_shutdown():

    manager = PluginManager(
        registry=PluginRegistry(),
        loader=FakeLoader(),
        runtime=FakeRuntime(),
    )

    plugin = await manager.load(
        "dummy.path"
    )

    await plugin.shutdown()

    assert plugin.shutdown_called is True