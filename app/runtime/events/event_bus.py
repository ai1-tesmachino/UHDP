from __future__ import annotations

from collections import defaultdict
from contextvars import ContextVar
import asyncio
import inspect
import logging
from threading import RLock

from .event import Event

logger = logging.getLogger(__name__)
_dispatching: ContextVar[frozenset[str]] = ContextVar(
    "runtime_event_dispatching",
    default=frozenset(),
)


class EventBus:
    """Bounded in-process event dispatcher with isolated subscribers."""

    def __init__(self, *, max_pending_handlers: int = 1000) -> None:
        if max_pending_handlers < 1:
            raise ValueError("max_pending_handlers must be positive")
        self._handlers: dict[str, list] = (
            defaultdict(list)
        )
        self._lock = RLock()
        self._pending_tasks: set[asyncio.Task] = set()
        self._max_pending_handlers = max_pending_handlers

    def subscribe(
        self,
        event_type: str,
        handler,
    ) -> None:
        with self._lock:
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: str,
        handler,
    ) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)
            if not handlers:
                self._handlers.pop(event_type, None)

    def handler_count(self, event_type: str) -> int:
        with self._lock:
            return len(self._handlers.get(event_type, []))

    def registered_events(self) -> list[str]:
        with self._lock:
            return list(self._handlers.keys())

    def _snapshot(self, event_type: str) -> tuple[list, list]:
        with self._lock:
            return (
                list(self._handlers.get(event_type, [])),
                list(self._handlers.get("*", [])),
            )

    def publish(self, event) -> None:
        """Synchronously deliver to sync handlers for legacy callers.

        New async runtime code should use ``publish_async`` so async
        subscribers are awaited rather than scheduled in the background.
        """
        active = _dispatching.get()
        if event.event_type in active:
            logger.error("Recursive publication blocked for event %s", event.event_type)
            return
        token = _dispatching.set(active | {event.event_type})
        try:
            event_handlers, wildcard_handlers = self._snapshot(event.event_type)
            for handler in (*event_handlers, *wildcard_handlers):
                if inspect.iscoroutinefunction(handler):
                    self._schedule(self._run_async_handler(handler, event))
                    continue
                try:
                    result = handler(event)
                    if inspect.isawaitable(result):
                        self._schedule(self._await_result(result, handler, event))
                except Exception:
                    logger.exception("Event handler failed for %s", event.event_type)
        finally:
            _dispatching.reset(token)

    async def publish_async(self, event) -> None:
        active = _dispatching.get()
        if event.event_type in active:
            logger.error("Recursive publication blocked for event %s", event.event_type)
            return
        token = _dispatching.set(active | {event.event_type})
        try:
            event_handlers, wildcard_handlers = self._snapshot(event.event_type)
            for handler in (*event_handlers, *wildcard_handlers):
                try:
                    if inspect.iscoroutinefunction(handler):
                        result = handler(event)
                    else:
                        result = await asyncio.to_thread(handler, event)
                    if inspect.isawaitable(result):
                        await result
                except Exception:
                    logger.exception(
                        "Event handler failed for %s",
                        event.event_type,
                    )
        finally:
            _dispatching.reset(token)

    async def _run_async_handler(self, handler, event) -> None:
        try:
            await handler(event)
        except Exception:
            logger.exception("Event handler failed for %s", event.event_type)

    async def _await_result(self, result, handler, event) -> None:
        try:
            await result
        except Exception:
            logger.exception(
                "Event handler failed for %s (%r)",
                event.event_type,
                handler,
            )

    def _schedule(self, coroutine) -> None:
        if len(self._pending_tasks) >= self._max_pending_handlers:
            coroutine.close()
            logger.error("Event handler capacity reached; delivery was rejected")
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            coroutine.close()
            logger.error("Async event handler requires an active event loop")
            return
        task = loop.create_task(coroutine)
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()

    async def wait_for_handlers(self, timeout: float = 1.0) -> None:
        pending = set(self._pending_tasks)
        if not pending:
            return
        _, unfinished = await asyncio.wait(pending, timeout=timeout)
        for task in unfinished:
            task.cancel()
        if unfinished:
            _, still_running = await asyncio.wait(unfinished, timeout=timeout)
            if still_running:
                logger.error(
                    "%d asynchronous event handler(s) ignored cancellation",
                    len(still_running),
                )

    def subscribe_all(self, handler):
        self.subscribe("*", handler)
