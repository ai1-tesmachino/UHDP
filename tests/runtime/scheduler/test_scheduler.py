from app.runtime.scheduler.job import Job
from app.runtime.scheduler.scheduler import Scheduler
from datetime import datetime, UTC, timedelta
from app.runtime.scheduler.triggers import OnceTrigger

def test_scheduler_add_job():
    scheduler = Scheduler()

    job = Job(
        name="test",
        callback=lambda: None,
    )

    scheduler.add_job(job)

    assert len(scheduler.jobs()) == 1

def test_due_jobs():
    scheduler = Scheduler()

    trigger = OnceTrigger(
        datetime.now(UTC) - timedelta(
            seconds=1
        )
    )

    job = Job(
        name="due-job",
        callback=lambda: None,
        trigger=trigger,
    )

    scheduler.add_job(job)

    assert len(scheduler.due_jobs()) == 1


def test_scheduler_start():
    scheduler = Scheduler()

    scheduler.start()

    assert scheduler.is_running is True

    scheduler.stop()

def test_scheduler_stop():
    scheduler = Scheduler()

    scheduler.start()
    scheduler.stop()

    assert scheduler.is_running is False

def test_disable_job():
    scheduler = Scheduler()

    job = Job(
        name="test",
        callback=lambda: None,
    )

    scheduler.add_job(job)

    scheduler.disable_job(job.job_id)

    assert job.enabled is False


def test_enable_job():
    scheduler = Scheduler()

    job = Job(
        name="test",
        callback=lambda: None,
    )

    scheduler.add_job(job)

    scheduler.disable_job(job.job_id)
    scheduler.enable_job(job.job_id)

    assert job.enabled is True




def test_scheduler_tick_executes_job():
    executed = False

    def callback():
        nonlocal executed
        executed = True

    scheduler = Scheduler()

    trigger = OnceTrigger(
        datetime.now(UTC) - timedelta(
            seconds=1
        )
    )

    job = Job(
        name="test",
        callback=callback,
        trigger=trigger,
    )

    scheduler.add_job(job)

    scheduler.tick()

    assert executed is True