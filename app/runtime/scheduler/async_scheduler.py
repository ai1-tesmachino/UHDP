from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC
import inspect
import logging
from typing import Any

from apscheduler.job import Job as APSchedulerJob
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus

logger = logging.getLogger(__name__)


class RuntimeScheduler:
    """Application-scoped APScheduler integration using the active event loop."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.scheduler = AsyncIOScheduler(timezone=UTC)
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self.scheduler.start()
        self._started = True
        await self.event_bus.publish_async(
            Event(event_type="scheduler.started", source="scheduler")
        )

    async def shutdown(self) -> None:
        if not self._started:
            return
        self.scheduler.shutdown(wait=False)
        await asyncio.sleep(0)
        self._started = False
        await self.event_bus.publish_async(
            Event(event_type="scheduler.stopped", source="scheduler")
        )

    def add_job(
        self,
        func: Callable,
        *,
        job_id: str,
        trigger: str = "interval",
        **trigger_options: Any,
    ) -> APSchedulerJob:
        if not self._started:
            raise RuntimeError("Scheduler is not running")
        if self.scheduler.get_job(job_id) is not None:
            raise ValueError(f"Scheduled job already exists: {job_id}")

        async def invoke() -> None:
            try:
                if inspect.iscoroutinefunction(func):
                    await func()
                else:
                    result = await asyncio.to_thread(func)
                    if inspect.isawaitable(result):
                        await result
            except Exception:
                logger.exception("Scheduled job %s failed", job_id)
                await self.event_bus.publish_async(
                    Event(
                        event_type="scheduler.failed",
                        source="scheduler",
                        payload={"job_id": job_id},
                    )
                )

        return self.scheduler.add_job(
            invoke,
            trigger=trigger,
            id=job_id,
            **trigger_options,
        )

    def remove_job(self, job_id: str) -> None:
        self.scheduler.remove_job(job_id)

    def get_jobs(self) -> list[APSchedulerJob]:
        return self.scheduler.get_jobs()

    def get_status(self) -> str:
        if self.scheduler.running:
            return "running"
        return "stopped"

    @property
    def running(self) -> bool:
        return self.scheduler.running
