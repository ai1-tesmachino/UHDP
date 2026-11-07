from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any


class StateManager:
    def __init__(self) -> None:
        self._state: dict[str, Any] = {}
        self._lock = RLock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = deepcopy(value)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return deepcopy(self._state.get(key, default))

    def remove(self, key: str) -> None:
        with self._lock:
            self._state.pop(key, None)

    def update(self, key: str, value: Any) -> None:
        with self._lock:
            if key not in self._state:
                raise KeyError(f"State key not found: {key}")
            self._state[key] = deepcopy(value)

    def delete(self, key: str) -> None:
        self.remove(key)

    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._state

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def snapshot(self) -> dict[str, Any]:
        return self.get_all()

    def clear(self) -> None:
        with self._lock:
            self._state.clear()