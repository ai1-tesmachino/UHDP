import time

from app.runtime.events.event_bus import EventBus
from app.runtime.scheduler.job import Job
from app.runtime.scheduler.scheduler import Scheduler
from app.runtime.scheduler.triggers import OnceTrigger

from datetime import datetime, UTC, timedelta


def demo_task():
    print("JOB EXECUTED")


def main():
    bus = EventBus()

    scheduler = Scheduler(event_bus=bus)

    trigger = OnceTrigger(
        datetime.now(UTC) + timedelta(seconds=3)
    )

    job = Job(
        name="demo-job",
        callback=demo_task,
        trigger=trigger,
    )

    scheduler.add_job(job)

    scheduler.start()

    time.sleep(5)

    scheduler.stop()


if __name__ == "__main__":
    main()