import pytest

from app.plugins.diagnostics.diagnostics_plugin import DiagnosticsPlugin
from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_registered_events_visible():
    bus = EventBus()

    plugin = DiagnosticsPlugin(bus)

    await plugin.initialize()

    events = plugin.get_registered_events()

    assert "*" in events
    

@pytest.mark.asyncio
async def test_wildcard_receives_all_events():
    bus = EventBus()

    plugin = DiagnosticsPlugin(bus)

    await plugin.initialize()

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

    assert plugin.get_event_count() == 2