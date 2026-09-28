from __future__ import annotations

from collections import defaultdict

from .event import Event
from .subscriptions import EventHandler


class EventBus:
    """
    In-process event dispatcher.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = (
            defaultdict(list)
        )

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def handler_count(self, event_type: str) -> int:
        return len(self._handlers.get(event_type, []))

    def registered_events(self) -> list[str]:
        return list(self._handlers.keys())

    def publish(self, event):
            handlers = self._handlers.get(event.event_type, [])

            for handler in handlers:
                handler(event)

            wildcard_handlers = self._handlers.get("*", [])

            for handler in wildcard_handlers:
                handler(event)
            

    def subscribe_all(self, handler):
        self.subscribe("*", handler)
