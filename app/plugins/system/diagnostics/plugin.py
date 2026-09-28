from app.plugins.base import BasePlugin
from app.plugins.models import PluginMetadata

from app.plugins.system.diagnostics.services import (
    HealthCheckService,
)

from app.plugins.system.diagnostics.task_services import (
    CreateTaskService,
)


class Plugin(BasePlugin):
    metadata = PluginMetadata(
        name="diagnostics",
        version="1.0.0",
        description="Runtime diagnostics",
    )

    async def initialize(self) -> None:
        self.services = [
            HealthCheckService(self.runtime),
            CreateTaskService(self.runtime),
        ]

    async def shutdown(self) -> None:
        pass