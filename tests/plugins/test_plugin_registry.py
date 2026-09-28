from app.plugins.registry import PluginRegistry

from tests.plugins.dummy_plugin import DummyPlugin


def test_register_plugin():

    registry = PluginRegistry()

    plugin = DummyPlugin()

    registry.register(plugin)

    assert plugin in registry.list()


def test_unregister_plugin():

    registry = PluginRegistry()

    plugin = DummyPlugin()

    registry.register(plugin)

    registry.unregister(plugin)

    assert plugin not in registry.list()