import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, object]) -> None:
        await asyncio.gather(
            *(self._send_to_client(websocket, message) for websocket in tuple(self._connections))
        )

    async def _send_to_client(
        self, websocket: WebSocket, message: dict[str, object]
    ) -> None:
        try:
            await websocket.send_json(message)
        except (OSError, RuntimeError, WebSocketDisconnect):
            self.disconnect(websocket)
            logger.info("Removed a disconnected WebSocket client")
