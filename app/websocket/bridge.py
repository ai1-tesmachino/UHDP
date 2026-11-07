from app.runtime.events.event_bus import EventBus
from app.websocket.manager import WebSocketManager


class EventBridge:
    def __init__(
        self,
        event_bus: EventBus,
        websocket_manager: WebSocketManager,
    ) -> None:
        self._event_bus = event_bus
        self._websocket_manager = websocket_manager

        self._events = [
            "runtime.started",
            "runtime.stopping",
            "runtime.stopped",
            "runtime.failed",
            "job.created",
            "job.started",
            "job.completed",
            "job.failed",
            "job.cancelled",
            "job.timed_out",
        ]
        self._registered = False

    def register(self) -> None:
        if self._registered:
            return
        for event_name in self._events:
            self._event_bus.subscribe(
                event_name,
                self._handle_event,
            )
        self._registered = True

    def unregister(self) -> None:
        if not self._registered:
            return
        for event_name in self._events:
            self._event_bus.unsubscribe(
                event_name,
                self._handle_event,
            )
        self._registered = False

    async def _handle_event(self, event) -> None:
        await self._websocket_manager.broadcast(
            {
                "type": event.event_type,
                "event_id": str(event.event_id),
                "timestamp": event.timestamp.isoformat(),
                "correlation_id": event.correlation_id,
                "payload": event.payload,
            }
        )