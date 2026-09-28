from app.plugins.base import BasePlugin
from app.plugins.models import PluginMetadata


class DummyPlugin(BasePlugin):
    metadata = PluginMetadata(
        name="dummy",
        version="1.0.0",
        description="Dummy test plugin",
    )

    def __init__(self):
        self.initialized = False
        self.shutdown_called = False

    async def initialize(self) -> None:
        self.initialized = True

    async def shutdown(self) -> None:
        self.shutdown_called = True