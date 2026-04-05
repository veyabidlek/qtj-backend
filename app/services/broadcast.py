import time

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger("locomotive.broadcast")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []
        self._last_pong: dict[WebSocket, float] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self._last_pong[websocket] = time.time()
        logger.info("ws_client_connected", total_clients=len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self._last_pong.pop(websocket, None)
        logger.info("ws_client_disconnected", total_clients=len(self.active_connections))

    async def send_ping(self, websocket: WebSocket) -> None:
        try:
            await websocket.send_json({"type": "ping"})
        except Exception:
            pass

    def record_pong(self, websocket: WebSocket) -> None:
        self._last_pong[websocket] = time.time()

    def is_pong_overdue(self, websocket: WebSocket, timeout: float = 60.0) -> bool:
        last = self._last_pong.get(websocket)
        if last is None:
            return True
        return (time.time() - last) > timeout

    async def broadcast(self, message: str) -> None:
        disconnected: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)
            self._last_pong.pop(conn, None)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)
