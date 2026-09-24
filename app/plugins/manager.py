from app.plugins.loader import PluginLoader
from app.plugins.registry import PluginRegistry


class PluginManager:
    def __init__(
        self,
        registry: PluginRegistry,
        loader: PluginLoader,
        runtime,
    ) -> None:
        self._registry = registry
        self._loader = loader
        self._runtime = runtime

    async def load(
        self,
        module_path: str,
    ):
        plugin = self._loader.load(
            module_path,
        )

        plugin.runtime = self._runtime

        if hasattr(plugin, "services"):
            for service in plugin.services:
                service.runtime = self._runtime

        await plugin.initialize()

        self._registry.register(
            plugin,
        )

        return plugin

    async def unload(
        self,
        name: str,
    ) -> None:
        plugin = self._registry.get(name)

        await plugin.shutdown()

        self._registry.unregister(name)

    def get(
        self,
        name: str,
    ):
        return self._registry.get(name)

    def list(self):
        return self._registry.list()

    def get_service(
        self,
        plugin_name: str,
        service_name: str,
    ):
        plugin = self.get(plugin_name)

        for service in plugin.services:
            if service.name == service_name:
                return service

        raise KeyError(service_name)