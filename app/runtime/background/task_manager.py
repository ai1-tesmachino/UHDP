from __future__ import annotations

import asyncio
from collections.abc import Callable
import inspect
import logging

from app.runtime.models.task import Task

logger = logging.getLogger(__name__)


class TaskManager:
    """Tracks long-running asyncio tasks and preserves the plugin task API."""

    def __init__(self, *, shutdown_timeout: float = 5.0) -> None:
        self.shutdown_timeout = shutdown_timeout
        self._tasks: dict[str, Task] = {}
        self._managed: dict[str, asyncio.Task] = {}
        self._started = False

    async def start(self) -> None:
        self._started = True

    def create_task(self, name: str) -> Task:
        task = Task(name=name)
        self._tasks[task.id] = task
        return task

    def start_task(self, name: str, func: Callable) -> Task:
        if not self._started:
            raise RuntimeError("Background task manager is not started")
        if name in self._managed:
            raise ValueError(f"Background task already exists: {name}")
        if not callable(func):
            raise TypeError("Background task must be callable")
        task_record = Task(name=name, status="queued")
        self._tasks[task_record.id] = task_record
        running = asyncio.create_task(
            self._run_task(task_record, func),
            name=f"uhdp-background-{name}",
        )
        self._managed[name] = running
        running.add_done_callback(
            lambda completed, task_name=name: self._task_done(task_name, completed)
        )
        return task_record

    async def _run_task(self, record: Task, func: Callable) -> None:
        record.status = "running"
        try:
            if inspect.iscoroutinefunction(func):
                result = func()
            else:
                result = await asyncio.to_thread(func)
            if inspect.isawaitable(result):
                await result
            record.status = "completed"
        except asyncio.CancelledError:
            record.status = "cancelled"
            raise
        except Exception:
            record.status = "failed"
            logger.exception("Background task %s failed", record.name)

    def _task_done(self, name: str, task: asyncio.Task) -> None:
        if self._managed.get(name) is task:
            self._managed.pop(name, None)

    async def stop_task(self, name: str) -> bool:
        running = self._managed.get(name)
        if running is None:
            return False
        running.cancel()
        try:
            await asyncio.wait_for(
                asyncio.shield(running),
                timeout=self.shutdown_timeout,
            )
        except (asyncio.CancelledError, asyncio.TimeoutError):
            logger.warning("Background task %s exceeded its stop bound", name)
        return True

    def get_task(self, task_id: str) -> Task:
        if task_id in self._tasks:
            return self._tasks[task_id]
        for record in self._tasks.values():
            if record.name == task_id:
                return record
        raise KeyError(task_id)

    def list_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    async def stop_all(self) -> None:
        tasks = list(self._managed.values())
        for task in tasks:
            task.cancel()
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=self.shutdown_timeout)
            if pending:
                logger.error("%d background task(s) ignored cancellation", len(pending))
        self._started = False
