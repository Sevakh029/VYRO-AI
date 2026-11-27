import logging
import threading
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Protocol

from vyro_controller.decide import decide as stub_decide
from vyro_controller.state import Action, SystemState

from .adapters import intersection_to_state
from .in_memory_state import InMemoryTrafficState
from .schemas import SignalCommand

logger = logging.getLogger(__name__)


class CommandPublisher(Protocol):
    def publish(
        self,
        signal_id: str,
        phase: int,
        hold_s: float,
        reason: str,
    ) -> SignalCommand: ...


class BackendOrchestrator:
    def __init__(
        self,
        traffic_state: InMemoryTrafficState,
        publisher: CommandPublisher,
        controller: Callable[[SystemState], Action | Iterable[Action]] = stub_decide,
        interval_s: float = 1.0,
        max_stale_s: float = 5.0,
        hold_s: float = 15.0,
    ) -> None:
        if interval_s <= 0:
            raise ValueError("interval_s must be positive")
        if max_stale_s <= 0:
            raise ValueError("max_stale_s must be positive")
        if hold_s <= 0:
            raise ValueError("hold_s must be positive")
        self.traffic_state = traffic_state
        self.publisher = publisher
        self.controller = controller
        self.interval_s = interval_s
        self.max_stale_s = max_stale_s
        self.hold_s = hold_s
        self._tick_lock = threading.Lock()
        self._thread_lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def tick(self) -> list[SignalCommand]:
        if not self._tick_lock.acquire(blocking=False):
            logger.debug("Skipped overlapping orchestrator tick")
            return []
        try:
            commands: list[SignalCommand] = []
            now = datetime.now(UTC)
            intersections = self.traffic_state.latest_intersections()
            if not intersections:
                logger.debug("No intersection state is available; skipping tick")
                return commands

            for intersection_id, intersection in sorted(intersections.items()):
                stale_s = (now - intersection.timestamp).total_seconds()
                if stale_s < 0 or stale_s > self.max_stale_s:
                    logger.warning(
                        "Skipped stale or invalid state for signal %s (age %.3fs)",
                        intersection_id,
                        stale_s,
                    )
                    continue

                state = intersection_to_state(intersection)
                try:
                    decisions = self.controller(state)
                except Exception:
                    logger.exception("Controller exception for signal %s", intersection_id)
                    continue

                if decisions is None:
                    continue
                action_items = [decisions] if isinstance(decisions, Action) else decisions
                for action in action_items:
                    command = self._publish_action(action)
                    if command is not None:
                        commands.append(command)
            return commands
        finally:
            self._tick_lock.release()

    def tick_once(self) -> list[SignalCommand]:
        return self.tick()

    def run_once(self) -> list[SignalCommand]:
        return self.tick()

    def _publish_action(self, action: Action) -> SignalCommand | None:
        try:
            if not isinstance(action, Action):
                raise TypeError("controller returned an unsupported action type")
            hold_s = getattr(action, "hold_s", self.hold_s)
            if (
                isinstance(action.phase_id, bool)
                or not isinstance(action.phase_id, int)
                or action.phase_id < 0
                or not isinstance(hold_s, (int, float))
                or isinstance(hold_s, bool)
                or hold_s <= 0
            ):
                logger.error(
                    "Rejected unsafe or invalid action for signal %s",
                    action.intersection_id,
                )
                return None
            return self.publisher.publish(
                action.intersection_id,
                action.phase_id,
                float(hold_s),
                action.reason,
            )
        except Exception:
            logger.exception(
                "Command publication failed for signal %s",
                getattr(action, "intersection_id", "unknown"),
            )
            return None

    def start(self) -> None:
        with self._thread_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name="vyro-backend-orchestrator",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._thread_lock:
            thread = self._thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2)

    def is_running(self) -> bool:
        with self._thread_lock:
            return self._thread is not None and self._thread.is_alive()

    def _run_loop(self) -> None:
        while not self._stop_event.wait(0):
            self.tick()
            if self._stop_event.wait(self.interval_s):
                break
