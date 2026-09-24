import importlib

from app.plugins.base import BasePlugin


class PluginLoader:
    def load(
        self,
        module_path: str,
    ) -> BasePlugin:
        module = importlib.import_module(
            module_path,
        )

        plugin_class = getattr(
            module,
            "Plugin",
        )

        return plugin_class()