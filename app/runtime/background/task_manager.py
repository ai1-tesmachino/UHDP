from app.runtime.models.task import Task


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def create_task(
        self,
        name: str,
    ) -> Task:
        task = Task(
            name=name,
        )

        self._tasks[task.id] = task

        return task

    def list_tasks(
        self,
    ) -> list[Task]:
        return list(
            self._tasks.values()
        )

    def get_task(
        self,
        task_id: str,
    ) -> Task:
        return self._tasks[task_id]