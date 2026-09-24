from app.plugins.task_service import (
    TaskPluginService,
)


class CreateTaskService(
    TaskPluginService,
):
    name = "create_task"

    async def execute(
        self,
        **kwargs,
    ):
        task = self.task_manager.create_task(
            name="diagnostics_task",
        )

        return task.model_dump()