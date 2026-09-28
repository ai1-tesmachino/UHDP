from app.runtime.events.event import Event
from app.runtime.events.events_type import EventTypes
from datetime import datetime, UTC

from .job import Job
from .job_store import JobStore

import threading
import time

class Scheduler:
    def __init__(self, event_bus=None):
        self.job_store = JobStore()
        self.event_bus = event_bus
        self._running = False
        self._thread = None
        self._interval = 1

    def add_job(self, job: Job) -> None:
        job.schedule()

        self.job_store.add(job)

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type=EventTypes.JOB_ADDED,
                    source="Scheduler",
                    payload={
                        "job_id": job.job_id,
                    },
                )
            )

            self.event_bus.publish(
                Event(
                    event_type=EventTypes.JOB_SCHEDULED,
                    source="Scheduler",
                    payload={
                        "job_id": job.job_id,
                        "next_run": str(job.next_run),
                    },
                )
            )

    def enable_job(self, job_id: str):
        job = self.job_store.get(job_id)

        if job is None:
            return

        job.enabled = True

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type=EventTypes.JOB_ENABLED,
                    source="Scheduler",
                    payload={"job_id": job_id},
                )
            )


    def disable_job(self, job_id: str):
        job = self.job_store.get(job_id)

        if job is None:
            return

        job.enabled = False

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type=EventTypes.JOB_DISABLED,
                    source="Scheduler",
                    payload={"job_id": job_id},
                )
            )


    def remove_job(self, job_id: str) -> None:
        self.job_store.remove(job_id)

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type=EventTypes.JOB_REMOVED,
                    source="Scheduler",
                    payload={"job_id": job_id},
                )
            )

    def execute_job(self, job_id: str):
        job = self.job_store.get(job_id)
        job.status = "running"
        if job is None:
            return None

        try:
            result = job.execute()

            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        event_type=EventTypes.JOB_EXECUTED,
                        source="Scheduler",
                        payload={"job_id": job_id},
                    )
                )

            return result

        except Exception as ex:
            if self.event_bus:
                self.event_bus.publish(
                    Event(
                        event_type=EventTypes.JOB_FAILED,
                        source="Scheduler",
                        payload={
                            "job_id": job_id,
                            "error": str(ex),
                        },
                    )
                )

            raise


    def get_job(self, job_id: str):
        return self.job_store.get(job_id)

    def jobs(self):
        return self.job_store.all()

    def due_jobs(self):
        now = datetime.now(UTC)

        return [
            job
            for job in self.job_store.all()
            if job.is_due(now)
        ]

    def tick(self):
        for job in self.due_jobs():
            self.execute_job(job.job_id)

            if job.trigger:
                job.schedule()

    def run_forever(self):
        while self._running:
            self.tick()
            time.sleep(self._interval)


    def start(self):
        if self._running:
            return

        self._running = True

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type=EventTypes.SCHEDULER_STARTED,
                    source="Scheduler",
                )
            )

        self._thread = threading.Thread(
            target=self.run_forever,
            daemon=True,
        )

        self._thread.start()


    def stop(self):
        self._running = False

        if self._thread:
            self._thread.join(timeout=2)

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    event_type=EventTypes.SCHEDULER_STOPPED,
                    source="Scheduler",
                )
            )


    @property
    def is_running(self):
        return self._running



    