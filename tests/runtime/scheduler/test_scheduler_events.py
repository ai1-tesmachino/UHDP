from app.runtime.events.event_bus import EventBus
from app.runtime.events.events_type import EventTypes
from app.runtime.scheduler.job import Job
from app.runtime.scheduler.scheduler import Scheduler
from app.runtime.scheduler.triggers import IntervalTrigger


def test_job_enabled_event():
    bus = EventBus()

    received = []

    bus.subscribe(
        EventTypes.JOB_ENABLED,
        lambda e: received.append(e),
    )

    scheduler = Scheduler(
        event_bus=bus,
    )

    job = Job(
        name="test",
        callback=lambda: None,
    )

    scheduler.add_job(job)

    scheduler.enable_job(job.job_id)

    assert len(received) == 1


def test_job_disabled_event():
    bus = EventBus()

    received = []

    bus.subscribe(
        EventTypes.JOB_DISABLED,
        lambda e: received.append(e),
    )

    scheduler = Scheduler(
        event_bus=bus,
    )

    job = Job(
        name="test",
        callback=lambda: None,
    )

    scheduler.add_job(job)

    scheduler.disable_job(job.job_id)

    assert len(received) == 1

    

def test_job_added_event():
    bus = EventBus()

    received = []

    bus.subscribe(
        EventTypes.JOB_ADDED,
        lambda e: received.append(e),
    )

    scheduler = Scheduler(event_bus=bus)

    scheduler.add_job(
        Job(
            name="test",
            callback=lambda: None,
        )
    )

    assert len(received) == 1


def test_job_removed_event():
    bus = EventBus()

    received = []

    bus.subscribe(
        EventTypes.JOB_REMOVED,
        lambda e: received.append(e),
    )

    scheduler = Scheduler(event_bus=bus)

    job = Job(
        name="test",
        callback=lambda: None,
    )

    scheduler.add_job(job)
    scheduler.remove_job(job.job_id)

    assert len(received) == 1


def test_job_executed_event():
    bus = EventBus()

    received = []

    bus.subscribe(
        EventTypes.JOB_EXECUTED,
        lambda e: received.append(e),
    )

    scheduler = Scheduler(event_bus=bus)

    job = Job(
        name="test",
        callback=lambda: "ok",
    )

    scheduler.add_job(job)

    scheduler.execute_job(job.job_id)

    assert len(received) == 1


def test_job_failed_event():
        bus = EventBus()

        received = []

        bus.subscribe(
            EventTypes.JOB_FAILED,
            lambda e: received.append(e),
        )

        scheduler = Scheduler(
            event_bus=bus,
        )

        def fail():
            raise RuntimeError("failure")

        job = Job(
            name="bad-job",
            callback=fail,
        )

        scheduler.add_job(job)

        try:
            scheduler.execute_job(job.job_id)
        except RuntimeError:
            pass

        assert len(received) == 1


def test_scheduler_started_event():
    bus = EventBus()

    received = []

    bus.subscribe(
        EventTypes.SCHEDULER_STARTED,
        lambda e: received.append(e),
    )

    scheduler = Scheduler(
        event_bus=bus,
    )

    scheduler.start()
    scheduler.stop()

    assert len(received) == 1


def test_job_scheduled_event():
    bus = EventBus()

    received = []

    bus.subscribe(
        EventTypes.JOB_SCHEDULED,
        lambda e: received.append(e),
    )

    scheduler = Scheduler(
        event_bus=bus,
    )

    scheduler.add_job(
        Job(
            name="test",
            callback=lambda: None,
            trigger=IntervalTrigger(10),
        )
    )

    assert len(received) == 1


def test_scheduler_stopped_event():
    bus = EventBus()

    received = []

    bus.subscribe(
        EventTypes.SCHEDULER_STOPPED,
        lambda e: received.append(e),
    )

    scheduler = Scheduler(
        event_bus=bus,
    )

    scheduler.start()
    scheduler.stop()

    assert len(received) == 1









