from collections import deque


class EventHistory:
    def __init__(self, max_events: int = 100):
        self._events = deque(maxlen=max_events)

    def add(self, event) -> None:
        self._events.append(event)

    def count(self) -> int:
        return len(self._events)

    def latest(self, limit: int = 10):
        return list(self._events)[-limit:]

    def clear(self) -> None:
        self._events.clear()