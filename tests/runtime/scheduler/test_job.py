from app.runtime.scheduler.job import Job
from app.runtime.scheduler.triggers import IntervalTrigger
from datetime import datetime, UTC, timedelta



def test_job_creation():
    job = Job(
        name="test",
        callback=lambda: None,
    )

    assert job.name == "test"
    assert job.job_id is not None


def test_job_defaults():
    job = Job(
        name="test",
        callback=lambda: None,
    )

    assert job.enabled is True
    assert job.status == "idle"

    
def test_job_schedule():
    job = Job(
        name="test",
        callback=lambda: None,
        trigger=IntervalTrigger(10),
    )

    job.schedule()

    assert job.next_run is not None


def test_job_is_due():
    job = Job(
        name="test",
        callback=lambda: None,
    )

    job.next_run = (
        datetime.now(UTC)
        - timedelta(seconds=1)
    )

    assert job.is_due(datetime.now(UTC))