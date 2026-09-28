from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus


def test_publish_event():
    bus = EventBus()

    received = []

    def handler(event):
        received.append(event)

    bus.subscribe(
        "test.event",
        handler,
    )

    bus.publish(
        Event(
            event_type="test.event",
            source="test",
        )
    )

    assert len(received) == 1


    def test_handler_count():
        bus = EventBus()

        def handler(event):
            pass

        bus.subscribe("test.event", handler)

        assert bus.handler_count("test.event") == 1


    def test_registered_events():
        bus = EventBus()

    def handler(event):
        pass

    bus.subscribe("event.one", handler)
    bus.subscribe("event.two", handler)

    events = bus.registered_events()

    assert "event.one" in events
    assert "event.two" in events


    def test_wildcard_subscription():
        bus = EventBus()

        received = []

        bus.subscribe_all(
            lambda e: received.append(e)
        )

        bus.publish(
            Event(
                event_type="event.one",
                source="test",
            )
        )

        bus.publish(
            Event(
                event_type="event.two",
                source="test",
            )
        )

        assert len(received) == 2