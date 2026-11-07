from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
import inspect
import logging
from typing import Any
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus
from app.runtime.models.status import JobStatus
from app.runtime.models.runtime import RuntimeJob

logger = logging.getLogger(__name__)


class JobManager:
    """Runs bounded, in-memory application jobs independently of diagnostics."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        *,
        max_concurrency: int = 4,
        max_queued_jobs: int = 100,
        retention_limit: int = 500,
        shutdown_timeout: float = 5.0,
        scheduler: AsyncIOScheduler | None = None,
    ) -> None:
        if max_concurrency < 1 or max_queued_jobs < 1:
            raise ValueError("Job limits must be positive")
        self.event_bus = event_bus
        self.max_concurrency = max_concurrency
        self.max_queued_jobs = max_queued_jobs
        self.retention_limit = retention_limit
        self.shutdown_timeout = shutdown_timeout
        self.scheduler = scheduler or AsyncIOScheduler(timezone=UTC)
        self._owns_scheduler = scheduler is None
        self._jobs: dict[str, RuntimeJob] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._cancel_requested: set[str] = set()
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._started = False
        self._accepting = False

    async def start(self) -> None:
        if self._started:
            return
        if self._owns_scheduler and not self.scheduler.running:
            self.scheduler.start()
        self._started = True
        self._accepting = True

    async def submit(
        self,
        job_type: str,
        func: Callable,
        *,
        timeout: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeJob:
        if not callable(func):
            raise TypeError("Job function must be callable")
        if timeout is not None and timeout <= 0:
            raise ValueError("Job timeout must be positive")
        async with self._lock:
            if not self._started or not self._accepting:
                raise RuntimeError("Job manager is not accepting new jobs")
            queued = sum(
                job.status is JobStatus.QUEUED for job in self._jobs.values()
            )
            if queued >= self.max_queued_jobs:
                raise RuntimeError("Job queue is full")
            job = RuntimeJob(
                job_type=job_type,
                status=JobStatus.QUEUED,
                metadata=metadata or {},
            )
            key = str(job.job_id)
            self._jobs[key] = job
            self._prune_completed()
        await self._publish("job.created", job)
        async with self._lock:
            if not self._accepting:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now(UTC)
                return job.model_copy(deep=True)
            task = asyncio.create_task(
                self._execute(key, func, timeout),
                name=f"uhdp-job-{key}",
            )
            self._tasks[key] = task
            task.add_done_callback(
                lambda completed, job_key=key: self._task_done(job_key, completed)
            )
        return job.model_copy(deep=True)

    async def _execute(
        self,
        job_id: str,
        func: Callable,
        timeout: float | None,
    ) -> None:
        job = self._jobs[job_id]
        async with self._semaphore:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            await self._publish("job.started", job)
            try:
                work = self._invoke(func)
                result = await asyncio.wait_for(work, timeout) if timeout else await work
                if job_id in self._cancel_requested:
                    job.status = JobStatus.CANCELLED
                    return
                job.result = result
                job.status = JobStatus.COMPLETED
                await self._publish("job.completed", job)
            except asyncio.TimeoutError:
                job.error = "Job execution timed out"
                job.status = JobStatus.TIMED_OUT
                await self._publish("job.timed_out", job)
            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                raise
            except Exception as exc:
                job.error = str(exc)
                job.status = JobStatus.FAILED
                logger.exception("Runtime job %s failed", job_id)
                await self._publish("job.failed", job)
            finally:
                job.completed_at = datetime.now(UTC)

    async def _invoke(self, func: Callable) -> Any:
        if inspect.iscoroutinefunction(func):
            return await func()
        result = await asyncio.to_thread(func)
        if inspect.isawaitable(result):
            return await result
        return result

    def _task_done(self, job_id: str, task: asyncio.Task) -> None:
        self._tasks.pop(job_id, None)
        self._cancel_requested.discard(job_id)
        if task.cancelled():
            job = self._jobs.get(job_id)
            if job and job.status not in (
                JobStatus.CANCELLED,
                JobStatus.TIMED_OUT,
            ):
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now(UTC)

    def cleanup_completed(self, *, older_than_seconds: float = 3600) -> int:
        cutoff = datetime.now(UTC).timestamp() - older_than_seconds
        expired = [
            key
            for key, job in self._jobs.items()
            if job.status in (
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.TIMED_OUT,
            )
            and job.completed_at is not None
            and job.completed_at.timestamp() < cutoff
        ]
        for key in expired:
            self._jobs.pop(key, None)
        return len(expired)

    async def _publish(self, event_type: str, job: RuntimeJob) -> None:
        if self.event_bus is None:
            return
        await self.event_bus.publish_async(
            Event(
                event_type=event_type,
                source="job_manager",
                payload={"job_id": str(job.job_id), "job_type": job.job_type},
                timestamp=datetime.now(UTC),
                correlation_id=job.metadata.get("correlation_id"),
            )
        )

    def _prune_completed(self) -> None:
        completed = [
            key for key, job in self._jobs.items()
            if job.status in (
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.TIMED_OUT,
            )
        ]
        while len(self._jobs) > self.retention_limit and completed:
            self._jobs.pop(completed.pop(0), None)

    def get_job(self, job_id: str | UUID) -> RuntimeJob | None:
        job = self._jobs.get(str(job_id))
        return job.model_copy(deep=True) if job else None

    def list_jobs(self, limit: int | None = None) -> list[RuntimeJob]:
        jobs = sorted(
            self._jobs.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )
        if limit is not None:
            jobs = jobs[:limit]
        return [job.model_copy(deep=True) for job in jobs]

    def get_active_jobs(self) -> list[RuntimeJob]:
        return [
            job for job in self.list_jobs()
            if job.status in (JobStatus.QUEUED, JobStatus.RUNNING)
        ]

    def get_job_result(self, job_id: str | UUID) -> Any:
        job = self.get_job(job_id)
        return None if job is None else job.result

    async def wait_for_job(
        self,
        job_id: str | UUID,
        timeout: float | None = None,
    ) -> RuntimeJob | None:
        task = self._tasks.get(str(job_id))
        if task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout)
            except asyncio.TimeoutError:
                pass
        return self.get_job(job_id)

    async def cancel_job(self, job_id: str | UUID) -> RuntimeJob | None:
        key = str(job_id)
        job = self._jobs.get(key)
        task = self._tasks.get(key)
        if job is None:
            return None
        if task is not None and not task.done():
            self._cancel_requested.add(key)
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(UTC)
            task.cancel()
            await self._publish("job.cancelled", job)
            try:
                await asyncio.wait_for(
                    asyncio.shield(task),
                    timeout=self.shutdown_timeout,
                )
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.warning("Job %s did not stop within the cancellation bound", key)
        return self.get_job(key)

    async def stop(self) -> None:
        self._accepting = False
        tasks = list(self._tasks.values())
        if not tasks:
            if self._owns_scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                await asyncio.sleep(0)
            self._started = False
            return
        _, pending = await asyncio.wait(tasks, timeout=self.shutdown_timeout)
        for task in pending:
            task.cancel()
        for job_id, task in tuple(self._tasks.items()):
            if task not in pending:
                continue
            self._cancel_requested.add(job_id)
            job = self._jobs.get(job_id)
            if job is not None:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now(UTC)
                await self._publish("job.cancelled", job)
        if pending:
            _, still_pending = await asyncio.wait(
                pending,
                timeout=self.shutdown_timeout,
            )
            if still_pending:
                logger.error("%d runtime job(s) ignored cancellation", len(still_pending))
        if self._owns_scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            await asyncio.sleep(0)
        self._started = False

    def reject_new_jobs(self) -> None:
        self._accepting = False
