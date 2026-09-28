from datetime import datetime, UTC, timedelta


class IntervalTrigger:
    def __init__(self, seconds: int):
        self.seconds = seconds

    def next_run(self) -> datetime:
        return datetime.now(UTC) + timedelta(
            seconds=self.seconds
        )


class OnceTrigger:
    def __init__(self, run_at: datetime):
        self.run_at = run_at

    def next_run(self) -> datetime:
        return self.run_at