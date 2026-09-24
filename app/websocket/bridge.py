from app.runtime.event_bus import EventBus
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
            "state.created",
            "state.updated",
            "state.deleted",
            "task.created",
            "task.started",
            "task.completed",
            "task.failed",
            "job.created",
            "job.started",
            "job.completed",
            "job.failed",
        ]

    def register(self) -> None:
        for event_name in self._events:
            self._event_bus.subscribe(
                event_name,
                self._handle_event,
            )

    def unregister(self) -> None:
        for event_name in self._events:
            self._event_bus.unsubscribe(
                event_name,
                self._handle_event,
            )

    async def _handle_event(self, event) -> None:
        await self._websocket_manager.broadcast(
            {
                "type": event.type,
                "payload": event.payload,
            }
        )