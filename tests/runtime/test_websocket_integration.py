import pytest

from app.runtime.events.event import Event
from app.runtime.events.event_bus import EventBus
from app.websocket.bridge import EventBridge


@pytest.mark.asyncio
async def test_runtime_events_are_broadcast_once_and_bridge_cleans_up():
    class Manager:
        def __init__(self):
            self.messages = []

        async def broadcast(self, message):
            self.messages.append(message)

    bus = EventBus()
    manager = Manager()
    bridge = EventBridge(bus, manager)
    event = Event(
        event_type="job.completed",
        source="job_manager",
        correlation_id="correlation-1",
        payload={"job_id": "job-1"},
    )

    bridge.register()
    bridge.register()
    await bus.publish_async(event)
    assert len(manager.messages) == 1
    assert manager.messages[0]["type"] == "job.completed"
    assert manager.messages[0]["correlation_id"] == "correlation-1"

    bridge.unregister()
    await bus.publish_async(event)
    assert len(manager.messages) == 1
