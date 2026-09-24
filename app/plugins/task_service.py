from app.plugins.services import PluginService


class TaskPluginService(PluginService):
    def __init__(
        self,
        runtime=None,
    ) -> None:
        self.runtime = runtime

    @property
    def task_manager(self):
        return self.runtime.task_manager

    @property
    def job_manager(self):
        return self.runtime.job_manager

    @property
    def event_bus(self):
        return self.runtime.event_bus