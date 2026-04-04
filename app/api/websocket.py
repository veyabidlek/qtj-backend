import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.broadcast import ConnectionManager

logger = logging.getLogger("locomotive")

router = APIRouter()

manager = ConnectionManager()


@router.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
