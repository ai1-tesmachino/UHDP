from app.runtime.scheduler.job import Job
import pytest

def test_job_failure():
    def fail():
        raise RuntimeError("boom")

    job = Job(
        name="failure",
        callback=fail,
    )

    with pytest.raises(RuntimeError):
        job.execute()

def test_job_execute():
    job = Job(
        name="test",
        callback=lambda: "success",
    )

    result = job.execute()

    assert result == "success"