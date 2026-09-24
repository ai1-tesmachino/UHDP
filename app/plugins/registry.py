from app.plugins.base import BasePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, BasePlugin] = {}

    def register(
        self,
        plugin: BasePlugin,
    ) -> None:
        self._plugins[plugin.metadata.name] = plugin

    def unregister(
        self,
        name: str,
    ) -> None:
        self._plugins.pop(name, None)

    def get(
        self,
        name: str,
    ) -> BasePlugin:
        return self._plugins[name]

    def exists(
        self,
        name: str,
    ) -> bool:
        return name in self._plugins

    def list(self) -> list[BasePlugin]:
        return list(self._plugins.values())