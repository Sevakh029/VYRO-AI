import asyncio
import logging
from threading import Lock

from pydantic import ValidationError

from .schemas import IntersectionState, SignalCommand, VehicleState
from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

MESSAGE_SCHEMAS = {
    "vyro/v1/vehicle/state": VehicleState,
    "vyro/v1/intersection/state": IntersectionState,
    "vyro/v1/controller/command": SignalCommand,
}


class MQTTMessageHandler:
    def __init__(self, websocket_manager: WebSocketManager) -> None:
        self.websocket_manager = websocket_manager
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_lock = Lock()

    def activate(self, loop: asyncio.AbstractEventLoop) -> None:
        with self._loop_lock:
            self._loop = loop

    def deactivate(self) -> None:
        with self._loop_lock:
            self._loop = None

    def __call__(self, topic: str, payload: bytes) -> bool | str:
        schema = MESSAGE_SCHEMAS.get(topic)
        if schema is None:
            logger.warning("Rejected MQTT message for unsupported topic %s", topic)
            return False

        try:
            message = schema.model_validate_json(payload)
        except ValidationError as exc:
            logger.warning(
                "Rejected invalid MQTT message for topic %s (%d validation errors)",
                topic,
                exc.error_count(),
            )
            return False

        message_data = message.model_dump(mode="json")
        with self._loop_lock:
            loop = self._loop
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(self._schedule_broadcast, message_data)
        entity_id = getattr(message, "vehicle_id", None) or getattr(
            message, "intersection_id", None
        )
        return entity_id or True

    def _schedule_broadcast(self, message: dict[str, object]) -> None:
        asyncio.create_task(self.websocket_manager.broadcast(message))
