from __future__ import annotations

from threading import RLock
from typing import Any


class RuntimeRegistry:
    """
    Central runtime service registry.

    Stores runtime-wide services and managers.
    """

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._lock = RLock()

    def register(self, name: str, service: Any) -> None:
        with self._lock:
            if name in self._services:
                raise ValueError(
                    f"Service already registered: {name}"
                )

            self._services[name] = service

    def unregister(self, name: str) -> None:
        with self._lock:
            self._services.pop(name, None)

    def get(self, name: str) -> Any:
        with self._lock:
            if name not in self._services:
                raise KeyError(
                    f"Service not found: {name}"
                )

            return self._services[name]

    def exists(self, name: str) -> bool:
        with self._lock:
            return name in self._services

    def clear(self) -> None:
        with self._lock:
            self._services.clear()

    def list_services(self) -> list[str]:
        with self._lock:
            return sorted(self._services.keys())