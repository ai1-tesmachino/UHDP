from __future__ import annotations

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class JobManager:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    async def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    async def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

            await asyncio.sleep(0)

    def schedule_interval(
        self,
        func,
        *,
        seconds: int,
        job_id: str,
    ):
        return self.scheduler.add_job(
            func,
            trigger="interval",
            seconds=seconds,
            id=job_id,
            replace_existing=True,
        )

    def schedule_once(
        self,
        func,
        *,
        run_date,
        job_id: str,
    ):
        return self.scheduler.add_job(
            func,
            trigger="date",
            run_date=run_date,
            id=job_id,
            replace_existing=True,
        )

    def remove_job(self, job_id: str) -> None:
        self.scheduler.remove_job(job_id)

    def list_jobs(self):
        return self.scheduler.get_jobs()
