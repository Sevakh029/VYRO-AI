import logging
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from .schemas import ControllerAck, SignalCommand

logger = logging.getLogger(__name__)


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

    def publish(self, intersection_id: str, phase_id: int, reason: str) -> SignalCommand:
        command = SignalCommand(
            intersection_id=intersection_id,
            phase_id=phase_id,
            reason=reason,
            timestamp=datetime.now(UTC),
            command_id=str(uuid.uuid4()),
            schema_version="v1.1",
        )
        with self._lock:
            self.pending[command.command_id] = command
        timer = threading.Timer(self.timeout_s, self._fallback, args=(command.command_id,))
        with self._lock:
            self._timers[command.command_id] = timer
        timer.start()
        self.publisher(command)
        return command

    def publish_batch(self, commands: list[dict[str, object]]) -> list[SignalCommand]:
        published: list[SignalCommand] = []
        for command in commands:
            published.append(
                self.publish(
                    str(command["intersection_id"]),
                    int(command["phase_id"]),
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
        if command is None:
            return False
        logger.info(
            "Command %s applied=%s for intersection %s",
            ack.command_id,
            ack.applied,
            ack.intersection_id,
        )
        return ack.applied

    def _fallback(self, command_id: str) -> None:
        with self._lock:
            command = self.pending.pop(command_id, None)
            self._timers.pop(command_id, None)
            if command is not None:
                self.fallback_count += 1
        if command is not None:
            logger.warning(
                "Command %s timed out; intersection %s must revert to fixed time",
                command_id,
                command.intersection_id,
            )

    def close(self) -> None:
        with self._lock:
            timers = list(self._timers.values())
            self._timers.clear()
            self.pending.clear()
        for timer in timers:
            timer.cancel()
