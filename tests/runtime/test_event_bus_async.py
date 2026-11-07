import pytest

from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_async_publish_awaits_handlers_and_isolates_failures():
    bus = EventBus()
    received = []

    async def failing_handler(event):
        raise RuntimeError("handler failure")

    async def handler(event):
        received.append(event.event_type)

    bus.subscribe("runtime.started", failing_handler)
    bus.subscribe("runtime.started", handler)
    await bus.publish_async(
        Event(event_type="runtime.started", source="test")
    )

    assert received == ["runtime.started"]


@pytest.mark.asyncio
async def test_recursive_event_type_is_blocked_and_unsubscribe_cleans_up():
    bus = EventBus()
    delivered = []

    async def recursive(event):
        delivered.append(event.event_type)
        await bus.publish_async(
            Event(event_type=event.event_type, source="recursive")
        )

    bus.subscribe("job.started", recursive)
    await bus.publish_async(Event(event_type="job.started", source="test"))
    assert delivered == ["job.started"]

    bus.unsubscribe("job.started", recursive)
    assert bus.handler_count("job.started") == 0
