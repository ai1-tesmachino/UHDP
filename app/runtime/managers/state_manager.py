from __future__ import annotations

from threading import RLock
from typing import Any


class StateManager:
    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._lock = RLock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._state.get(key, default)

    def remove(self, key: str) -> None:
        with self._lock:
            self._state.pop(key, None)

    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._state

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)