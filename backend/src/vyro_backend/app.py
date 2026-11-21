import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .message_handler import MQTTMessageHandler
from .mqtt_subscriber import MQTTSubscriber
from .websocket_manager import WebSocketManager

websocket_manager = WebSocketManager()
mqtt_message_handler = MQTTMessageHandler(websocket_manager)
mqtt_subscriber = MQTTSubscriber(
    host=os.getenv("MQTT_HOST", "127.0.0.1"),
    port=int(os.getenv("MQTT_PORT", "1883")),
    on_message=mqtt_message_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    mqtt_message_handler.activate(asyncio.get_running_loop())
    try:
        await asyncio.to_thread(mqtt_subscriber.start)
        yield
    finally:
        mqtt_message_handler.deactivate()
        await asyncio.to_thread(mqtt_subscriber.stop)


app = FastAPI(title="VYRO Backend", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket_manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        websocket_manager.disconnect(websocket)
