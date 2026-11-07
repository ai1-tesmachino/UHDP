import asyncio
from collections.abc import Iterable
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(
        self,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(
        self,
        websocket: WebSocket,
    ) -> None:
        self._connections.discard(websocket)

    async def broadcast(
        self,
        message: dict,
    ) -> None:
        async def send(websocket: WebSocket) -> WebSocket | None:
            try:
                await asyncio.wait_for(
                    websocket.send_json(message),
                    timeout=1.0,
                )
                return None
            except Exception:
                logger.debug("Removing disconnected WebSocket client", exc_info=True)
                return websocket

        disconnected = await asyncio.gather(
            *(send(websocket) for websocket in tuple(self._connections))
        )
        for websocket in disconnected:
            if websocket is None:
                continue
            self.disconnect(websocket)

    @property
    def connections(self) -> Iterable[WebSocket]:
        return self._connections

    def connection_count(self) -> int:
        return len(self._connections)