from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
) -> None:
    manager = websocket.app.state.runtime.websocket_manager

    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)