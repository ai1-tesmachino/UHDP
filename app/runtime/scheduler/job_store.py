from .job import Job


class JobStore:
    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def add(self, job: Job) -> None:
        self._jobs[job.job_id] = job

    def remove(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def all(self) -> list[Job]:
        return list(self._jobs.values())

    def count(self) -> int:
        return len(self._jobs)

    def exists(self, job_id: str) -> bool:
         return job_id in self._jobs