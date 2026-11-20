import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .mqtt_subscriber import MQTTSubscriber

mqtt_subscriber = MQTTSubscriber(
    host=os.getenv("MQTT_HOST", "127.0.0.1"),
    port=int(os.getenv("MQTT_PORT", "1883")),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    mqtt_subscriber.start()
    try:
        yield
    finally:
        mqtt_subscriber.stop()


app = FastAPI(title="VYRO Backend", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
