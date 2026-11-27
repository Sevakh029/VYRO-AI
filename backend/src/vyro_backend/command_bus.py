import logging
import threading
import time
import uuid
from collections.abc import Callable
from typing import Protocol

from pydantic import ValidationError

from .schemas import ControllerAck, SignalCommand
from .timestamps import utc_now

logger = logging.getLogger(__name__)

COMMAND_TOPIC = "vyro/v1/controller/command"
ACK_TOPIC = "vyro/v1/controller/ack"


class MQTTBridge(Protocol):
    def publish(self, topic: str, payload: str, qos: int) -> object: ...


class MQTTCommandPublisher:
    def __init__(self, bridge: MQTTBridge) -> None:
        self.bridge = bridge

    def __call__(self, command: SignalCommand) -> object:
        try:
            result = self.bridge.publish(COMMAND_TOPIC, command.model_dump_json(), qos=1)
        except Exception as exc:
            logger.exception("Failed to publish MQTT command %s", command.command_id)
            raise RuntimeError("MQTT command publication failed") from exc
        rc = getattr(result, "rc", 0)
        if rc != 0:
            raise RuntimeError(f"MQTT command publication failed with rc={rc}")
        return result


class CommandBus:
    def __init__(
        self,
        publisher: Callable[[SignalCommand], object],
        timeout_s: float = 2.0,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        self.publisher = publisher
        self.timeout_s = timeout_s
        self.pending: dict[str, SignalCommand] = {}
        self.acks: dict[str, ControllerAck] = {}
        self._lock = threading.Lock()
        self._timers: dict[str, threading.Timer] = {}
        self.fallback_count = 0
        self.latency_samples_s: list[float] = []
        self._published_at: dict[str, float] = {}
        self.statuses: dict[str, dict[str, object]] = {}

    def publish(
        self,
        signal_id: str,
        phase: int,
        hold_s: float,
        reason: str,
    ) -> SignalCommand:
        command = SignalCommand(
            command_id=str(uuid.uuid4()),
            signal_id=signal_id,
            phase=phase,
            hold_s=hold_s,
            reason=reason,
            ts_utc=utc_now(),
            schema_version="0.2",
        )
        with self._lock:
            self.pending[command.command_id] = command
            self.statuses[command.command_id] = {"status": "pending"}
        timer = threading.Timer(self.timeout_s, self._fallback, args=(command.command_id,))
        with self._lock:
            self._timers[command.command_id] = timer
        timer.start()
        self._published_at[command.command_id] = time.monotonic()
        try:
            result = self.publisher(command)
            if result is False:
                raise RuntimeError("MQTT command publication returned failure")
        except Exception as exc:
            with self._lock:
                self.pending.pop(command.command_id, None)
                timer.cancel()
                self._timers.pop(command.command_id, None)
                self._published_at.pop(command.command_id, None)
                self.statuses[command.command_id] = {
                    "status": "publish_failed",
                    "reason": str(exc),
                }
            logger.error("Command %s publication failed: %s", command.command_id, exc)
            raise
        return command

    def publish_batch(self, commands: list[dict[str, object]]) -> list[SignalCommand]:
        published: list[SignalCommand] = []
        for command in commands:
            published.append(
                self.publish(
                    str(command["signal_id"]),
                    int(command["phase"]),
                    float(command["hold_s"]),
                    str(command["reason"]),
                )
            )
        return published

    def acknowledge(self, ack: ControllerAck) -> bool:
        with self._lock:
            command = self.pending.pop(ack.command_id, None)
            timer = self._timers.pop(ack.command_id, None)
            self.acks[ack.command_id] = ack
        if timer is not None:
            timer.cancel()
        published_at = self._published_at.pop(ack.command_id, None)
        if published_at is not None:
            self.latency_samples_s.append(time.monotonic() - published_at)
        if command is None:
            self.statuses[ack.command_id] = {
                "status": "unknown",
                "reason": "acknowledgment has no matching pending command",
                "ack": ack.model_dump(mode="json"),
            }
            logger.warning("Received unmatched acknowledgment %s", ack.command_id)
            return False
        if (
            ack.signal_id != command.signal_id
            or ack.phase != command.phase
            or ack.hold_s != command.hold_s
        ):
            self.statuses[ack.command_id] = {
                "status": "rejected",
                "reason": "acknowledgment fields do not match the command",
                "ack": ack.model_dump(mode="json"),
            }
            logger.error("Acknowledgment %s does not match command %s", ack.command_id, command.command_id)
            return False
        status = "applied" if ack.applied else "rejected"
        self.statuses[ack.command_id] = {
            "status": status,
            "reason": ack.reason,
            "ack": ack.model_dump(mode="json"),
        }
        logger.info(
            "Command %s status=%s for signal %s",
            ack.command_id,
            status,
            ack.signal_id,
        )
        return ack.applied

    def _fallback(self, command_id: str) -> None:
        with self._lock:
            command = self.pending.pop(command_id, None)
            self._timers.pop(command_id, None)
            if command is not None:
                self.fallback_count += 1
                self.statuses[command_id] = {
                    "status": "timeout",
                    "reason": "acknowledgment timeout",
                    "signal_id": command.signal_id,
                }
        if command is not None:
            logger.warning(
                "Command %s timed out; signal %s must revert to fixed time",
                command_id,
                command.signal_id,
            )

    def close(self) -> None:
        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
            self.pending.clear()
        for timer in timers:
            timer.cancel()


class AcknowledgementHandler:
    def __init__(self, bus: CommandBus) -> None:
        self.bus = bus

    def receive(self, topic: str, payload: bytes) -> bool:
        if topic != ACK_TOPIC:
            return True
        try:
            ack = ControllerAck.model_validate_json(payload)
        except ValidationError as exc:
            logger.warning("Rejected malformed MQTT acknowledgment (%d errors)", exc.error_count())
            return False
        return self.bus.acknowledge(ack)
