from app.plugins.base import BasePlugin
from app.plugins.capabilities import PluginCapability
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
        description="System diagnostics plugin",
        capabilities=[
            PluginCapability.DIAGNOSTICS,
        ],
    )

    services = [
        HealthCheckService(),
        CreateTaskService(),
    ]

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass