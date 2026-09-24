from collections.abc import Iterable

from fastapi import WebSocket


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
        disconnected: list[WebSocket] = []

        for websocket in self._connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)

    @property
    def connections(self) -> Iterable[WebSocket]:
        return self._connections

    def connection_count(self) -> int:
        return len(self._connections)