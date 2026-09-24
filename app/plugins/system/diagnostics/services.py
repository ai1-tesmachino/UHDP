from app.plugins.task_service import (
    TaskPluginService,
)

class HealthCheckService(
    TaskPluginService,
):
    name = "health_check"

    async def execute(
        self,
        **kwargs,
    ):
        return {
            "status": "healthy",
            "task_count": len(
                self.task_manager.list_tasks()
            ),
        }