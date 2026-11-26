import asyncio
import logging
from threading import Lock

from pydantic import ValidationError

from .command_bus import AcknowledgementHandler
from .in_memory_state import InMemoryTrafficState
from .schemas import (
    ControllerAck,
    IntersectionState,
    MetricsSnapshot,
    PreemptionRequest,
    SignalCommand,
    VehicleAdvisory,
    VehicleState,
)
from .sqlite_logger import SQLiteMessageLogger
from .validation import RateLimiter, validate_vehicle_state
from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)
MAX_PAYLOAD_BYTES = 1_048_576

MESSAGE_SCHEMAS = {
    "vyro/v1/vehicle/state": VehicleState,
    "vyro/v1/intersection/state": IntersectionState,
    "vyro/v1/controller/command": SignalCommand,
    "vyro/v1/controller/ack": ControllerAck,
    "vyro/v1/vehicle/advisory": VehicleAdvisory,
    "vyro/v1/metrics/snapshot": MetricsSnapshot,
    "vyro/v1/preemption/request": PreemptionRequest,
}


class MQTTMessageHandler:
    def __init__(
        self,
        websocket_manager: WebSocketManager,
        sqlite_logger: SQLiteMessageLogger | None = None,
        traffic_state: InMemoryTrafficState | None = None,
        acknowledgement_handler: AcknowledgementHandler | None = None,
    ) -> None:
        self.websocket_manager = websocket_manager
        self.sqlite_logger = sqlite_logger
        self.traffic_state = traffic_state
        self.acknowledgement_handler = acknowledgement_handler
        self.rate_limiter = RateLimiter()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_lock = Lock()

    def activate(self, loop: asyncio.AbstractEventLoop) -> None:
        with self._loop_lock:
            self._loop = loop

    def deactivate(self) -> None:
        with self._loop_lock:
            self._loop = None

    def __call__(self, topic: str, payload: bytes) -> bool | str:
        if len(payload) > MAX_PAYLOAD_BYTES:
            logger.warning("Rejected oversized MQTT message for topic %s", topic)
            if self.sqlite_logger is not None:
                self.sqlite_logger.log_async(
                    topic, payload, valid=False, error="oversized payload"
                )
            return False
        if not self.rate_limiter.allow():
            logger.warning("Rejected MQTT message for topic %s due to rate limit", topic)
            if self.sqlite_logger is not None:
                self.sqlite_logger.log_async(
                    topic, payload, valid=False, error="rate limit exceeded"
                )
            return False
        schema = MESSAGE_SCHEMAS.get(topic)
        if schema is None:
            if self.sqlite_logger is not None:
                self.sqlite_logger.log_async(
                    topic, payload, valid=False, error="unsupported topic"
                )
            logger.warning("Rejected MQTT message for unsupported topic %s", topic)
            return False

        try:
            message = schema.model_validate_json(payload)
        except ValidationError as exc:
            if self.sqlite_logger is not None:
                self.sqlite_logger.log_async(
                    topic, payload, valid=False, error="schema validation failed"
                )
            logger.warning(
                "Rejected invalid MQTT message for topic %s (%d validation errors)",
                topic,
                exc.error_count(),
            )
            return False
        if isinstance(message, VehicleState) and not validate_vehicle_state(message):
            if self.sqlite_logger is not None:
                self.sqlite_logger.log_async(
                    topic, payload, valid=False, error="vehicle state rejected"
                )
            logger.warning("Rejected off-network or impossible vehicle state")
            return False
        if self.sqlite_logger is not None:
            self.sqlite_logger.log_async(topic, payload, valid=True)
        if (
            isinstance(message, ControllerAck)
            and self.acknowledgement_handler is not None
        ):
            self.acknowledgement_handler.receive(topic, payload)

        message_data = message.model_dump(mode="json")
        if self.traffic_state is not None:
            if isinstance(message, VehicleState):
                self.traffic_state.receive_vehicle(message)
            elif isinstance(message, IntersectionState):
                self.traffic_state.receive_intersection(message)
            elif isinstance(message, SignalCommand):
                self.traffic_state.receive_command(message)
        with self._loop_lock:
            loop = self._loop
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(self._schedule_broadcast, topic, message_data)
        entity_id = getattr(message, "vehicle_id", None) or getattr(
            message, "signal_id", None
        ) or getattr(
            message, "intersection_id", None
        )
        return entity_id or True

    def _schedule_broadcast(self, topic: str, message: dict[str, object]) -> None:
        asyncio.create_task(self.websocket_manager.broadcast({**message, "topic": topic}))
