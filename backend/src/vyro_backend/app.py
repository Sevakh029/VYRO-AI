import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .in_memory_state import InMemoryTrafficState
from .latency import LatencyHistogram
from .message_handler import MQTTMessageHandler
from .mqtt_subscriber import MQTTSubscriber
from .sqlite_logger import SQLiteMessageLogger
from .websocket_manager import WebSocketManager

websocket_manager = WebSocketManager()
traffic_state = InMemoryTrafficState()
command_latency = LatencyHistogram()
sqlite_message_logger = SQLiteMessageLogger(
    os.getenv("VYRO_SQLITE_DB_PATH", "data/vyro_messages.db")
)
mqtt_message_handler = MQTTMessageHandler(
    websocket_manager,
    sqlite_message_logger,
    traffic_state,
)
mqtt_subscriber = MQTTSubscriber(
    host=os.getenv("MQTT_HOST", "127.0.0.1"),
    port=int(os.getenv("MQTT_PORT", "1883")),
    on_message=mqtt_message_handler,
    username=os.getenv("MQTT_USERNAME"),
    password=os.getenv("MQTT_PASSWORD"),
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
        await asyncio.to_thread(sqlite_message_logger.close)


app = FastAPI(title="VYRO Backend", version="0.1.0", lifespan=lifespan)


class ScenarioRequest(BaseModel):
    name: str = Field(default="normal", min_length=1, max_length=64)
    action: str = Field(default="start", pattern="^(start|stop|reset)$")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/state")
async def state() -> dict[str, object]:
    return traffic_state.snapshot()


@app.get("/metrics/command-latency")
async def command_latency_metrics() -> dict[str, object]:
    return command_latency.snapshot()


@app.post("/scenario")
async def scenario(request: ScenarioRequest) -> dict[str, object]:
    status = "stopped"
    if request.action == "start":
        status = "running"
    elif request.action == "reset":
        status = "stopped"
    traffic_state.set_scenario(request.name, status)
    return traffic_state.snapshot()["scenario"]


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
