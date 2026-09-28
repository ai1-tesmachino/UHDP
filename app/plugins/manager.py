from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry


class PluginManager:
    def __init__(
        self,
        registry: PluginRegistry,
        loader: PluginLoader,
        runtime=None,
    ) -> None:
        self._registry = registry
        self._loader = loader
        self._runtime = runtime

    async def load(
        self,
        module_path: str,
    ):
        plugin = self._loader.load(
            module_path
        )

        if self._runtime is not None:
            plugin.runtime = self._runtime

        await plugin.initialize()

        self._registry.register(
            plugin
        )

        return plugin

    def list(self):
        return self._registry.list()

    async def shutdown(self):
        for plugin in self._registry.list():
            await plugin.shutdown()