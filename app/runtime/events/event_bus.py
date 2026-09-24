from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable

from app.runtime.models import RuntimeEvent


EventHandler = Callable[[RuntimeEvent], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(
        self,
        event: RuntimeEvent,
    ) -> None:
        handlers = self._subscribers.get(
            event.event_type.value,
            [],
        )

        if not handlers:
            return

        await asyncio.gather(
            *[handler(event) for handler in handlers]
        )