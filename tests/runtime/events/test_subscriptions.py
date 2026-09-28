from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus


def test_multiple_handlers():
    bus = EventBus()

    count = 0

    def handler1(event):
        nonlocal count
        count += 1

    def handler2(event):
        nonlocal count
        count += 1

    bus.subscribe("test.event", handler1)
    bus.subscribe("test.event", handler2)

    bus.publish(
        Event(
            event_type="test.event",
            source="test",
        )
    )

    assert count == 2


def test_unsubscribe():
    bus = EventBus()

    count = 0

    def handler(event):
        nonlocal count
        count += 1

    bus.subscribe(
        "test.event",
        handler,
    )

    bus.unsubscribe(
        "test.event",
        handler,
    )

    bus.publish(
        Event(
            event_type="test.event",
            source="test",
        )
    )

    assert count == 0