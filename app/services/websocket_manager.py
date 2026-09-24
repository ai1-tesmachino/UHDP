from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.connections={}

    async def connect(self,session_id:str,websocket:WebSocket):
        await websocket.accept()
        self.connections[session_id]=websocket

    def disconnect(self,session_id:str):
        self.connections.pop(session_id,None)

    async def send(self,session_id:str,payload:dict):
        ws=self.connections.get(session_id)
        if ws:
            await ws.send_json(payload)
