from app.runtime.events.event import Event


def test_event_creation():
    event = Event(
        event_type="test.event",
        source="test",
    )

    assert event.event_type == "test.event"
    assert event.source == "test"
    assert event.event_id is not None