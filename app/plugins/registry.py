from app.plugins.base import BasePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins = {}

    def register(
        self,
        plugin,
    ) -> None:
        self._plugins[
            plugin.metadata.name
        ] = plugin

    def unregister(
        self,
        plugin,
    ) -> None:
        self._plugins.pop(
            plugin.metadata.name,
            None,
        )

    def get(
        self,
        name: str,
    ):
        return self._plugins.get(name)

    def exists(
        self,
        name: str,
    ) -> bool:
        return name in self._plugins

    def list(self):
        return list(
            self._plugins.values()
        )