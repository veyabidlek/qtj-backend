import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.broadcast import ConnectionManager

logger = get_logger("locomotive.websocket")

router = APIRouter()

manager = ConnectionManager()

PING_INTERVAL = 30  # seconds
PONG_TIMEOUT = 60   # seconds


async def _ping_loop(websocket: WebSocket, mgr: ConnectionManager) -> None:
    """Send ping every PING_INTERVAL seconds; disconnect if pong overdue."""
    try:
        while True:
            await asyncio.sleep(PING_INTERVAL)
            if mgr.is_pong_overdue(websocket, PONG_TIMEOUT):
                logger.warning("ws_pong_timeout", reason="no pong received within timeout")
                await websocket.close()
                return
            await mgr.send_ping(websocket)
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


@router.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await manager.connect(websocket)
    ping_task = asyncio.create_task(_ping_loop(websocket, manager))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("type") == "pong":
                    manager.record_pong(websocket)
            except (json.JSONDecodeError, TypeError):
                pass
    except WebSocketDisconnect:
        pass
    finally:
        ping_task.cancel()
        manager.disconnect(websocket)
