from app.runtime.scheduler.job import Job
from app.runtime.scheduler.job_store import JobStore


def test_add_job():
    store = JobStore()

    job = Job(
        name="test",
        callback=lambda: None,
    )

    store.add(job)

    assert store.count() == 1


def test_remove_job():
    store = JobStore()

    job = Job(
        name="test",
        callback=lambda: None,
    )

    store.add(job)
    store.remove(job.job_id)

    assert store.count() == 0


def test_job_exists():
    store = JobStore()

    job = Job(
        name="test",
        callback=lambda: None,
    )

    store.add(job)

    assert store.exists(job.job_id)