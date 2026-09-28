from app.runtime.scheduler.triggers import IntervalTrigger
from datetime import datetime, UTC, timedelta
from app.runtime.scheduler.triggers import OnceTrigger

def test_interval_trigger():
    trigger = IntervalTrigger(10)

    next_run = trigger.next_run()

    assert next_run is not None


def test_once_trigger():
    run_at = datetime.now(UTC) + timedelta(
        seconds=60
    )

    trigger = OnceTrigger(run_at)

    assert trigger.next_run() == run_at