from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import uuid4
from collections.abc import Callable


@dataclass(slots=True)
class Job:
    name: str
    callback: Callable
    trigger: object | None = None

    enabled: bool = True
    status: str = "idle"

    job_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    next_run: datetime | None = None
    last_run: datetime | None = None

    def execute(self):
        return self.callback()

    def schedule(self):
        if self.trigger:
            self.next_run = self.trigger.next_run()

    def is_due(self, now):
        return (
            self.enabled
            and self.next_run is not None
            and self.next_run <= now
        )