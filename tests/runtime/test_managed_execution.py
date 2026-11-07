import asyncio

import pytest

from app.runtime.background.task_manager import TaskManager
from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus
from app.runtime.managers.job_manager import JobManager
from app.runtime.models.status import JobStatus
from app.runtime.scheduler.async_scheduler import RuntimeScheduler


@pytest.mark.asyncio
async def test_job_lifecycle_result_failure_and_timeout():
    bus = EventBus()
    events = []
    bus.subscribe("job.completed", lambda event: events.append(event.event_type))
    manager = JobManager(bus)
    await manager.start()

    job = await manager.submit("simple", lambda: 42)
    completed = await manager.wait_for_job(job.job_id, timeout=1)
    assert completed.status is JobStatus.COMPLETED
    assert manager.get_job_result(job.job_id) == 42
    assert events == ["job.completed"]

    async def fail():
        raise ValueError("expected")

    failed = await manager.submit("failure", fail)
    failed = await manager.wait_for_job(failed.job_id, timeout=1)
    assert failed.status is JobStatus.FAILED
    assert failed.error == "expected"

    async def too_slow():
        await asyncio.sleep(1)

    timed_out = await manager.submit("timeout", too_slow, timeout=0.01)
    timed_out = await manager.wait_for_job(timed_out.job_id, timeout=1)
    assert timed_out.status is JobStatus.TIMED_OUT

    await manager.stop()
    with pytest.raises(RuntimeError, match="not accepting"):
        await manager.submit("after-stop", lambda: None)


@pytest.mark.asyncio
async def test_job_cancellation_and_concurrency_limit():
    manager = JobManager(max_concurrency=1, max_queued_jobs=2)
    await manager.start()
    started = asyncio.Event()

    async def long_job():
        started.set()
        await asyncio.sleep(10)

    job = await manager.submit("long", long_job)
    await asyncio.wait_for(started.wait(), timeout=1)
    cancelled = await manager.cancel_job(job.job_id)
    assert cancelled.status is JobStatus.CANCELLED
    await manager.stop()


@pytest.mark.asyncio
async def test_job_cancellation_remains_cancelled_if_callback_suppresses_it():
    manager = JobManager(max_concurrency=1)
    await manager.start()
    started = asyncio.Event()
    never = asyncio.Event()

    async def suppress_cancellation():
        started.set()
        try:
            await never.wait()
        except asyncio.CancelledError:
            return "suppressed"

    job = await manager.submit("suppress", suppress_cancellation)
    await asyncio.wait_for(started.wait(), timeout=1)
    cancelled = await manager.cancel_job(job.job_id)

    assert cancelled.status is JobStatus.CANCELLED
    assert cancelled.result is None
    await manager.stop()


@pytest.mark.asyncio
async def test_job_manager_rejects_work_when_queue_is_full():
    manager = JobManager(max_concurrency=1, max_queued_jobs=1)
    await manager.start()
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocked():
        started.set()
        await release.wait()

    first = await manager.submit("active", blocked)
    await asyncio.wait_for(started.wait(), timeout=1)
    second = await manager.submit("queued", blocked)
    with pytest.raises(RuntimeError, match="queue is full"):
        await manager.submit("rejected", blocked)

    release.set()
    await manager.wait_for_job(first.job_id, timeout=1)
    await manager.wait_for_job(second.job_id, timeout=1)
    await manager.stop()


@pytest.mark.asyncio
async def test_background_task_tracking_and_scheduler_shutdown():
    manager = TaskManager(shutdown_timeout=0.5)
    await manager.start()
    entered = asyncio.Event()

    async def long_running():
        entered.set()
        await asyncio.Event().wait()

    record = manager.start_task("monitor", long_running)
    await asyncio.wait_for(entered.wait(), timeout=1)
    assert manager.get_task("monitor").status == "running"
    assert await manager.stop_task("monitor")
    assert record.status == "cancelled"
    await manager.stop_all()

    bus = EventBus()
    scheduler = RuntimeScheduler(bus)
    await scheduler.start()
    calls = []
    scheduler.add_job(
        lambda: calls.append("tick"),
        job_id="test-tick",
        trigger="interval",
        seconds=0.02,
    )
    await asyncio.wait_for(_wait_for_call(calls), timeout=1)
    await scheduler.shutdown()
    count = len(calls)
    await asyncio.sleep(0.05)
    assert len(calls) == count
    assert scheduler.get_status() == "stopped"


async def _wait_for_call(calls):
    while not calls:
        await asyncio.sleep(0.005)
