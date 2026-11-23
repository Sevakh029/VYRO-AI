import math
import threading
import time
from collections import deque

from .schemas import VehicleState


def validate_vehicle_state(state: VehicleState) -> bool:
    if not math.isfinite(state.latitude) or not math.isfinite(state.longitude):
        return False
    if not math.isfinite(state.speed_mps) or state.speed_mps < 0:
        return False
    if not -90 <= state.latitude <= 90 or not -180 <= state.longitude <= 180:
        return False
    return True


class RateLimiter:
    def __init__(self, max_messages_per_second: float = 1500.0) -> None:
        if max_messages_per_second <= 0:
            raise ValueError("max_messages_per_second must be positive")
        self.max_messages_per_second = max_messages_per_second
        self._events: deque[float] = deque()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        window_start = now - 1.0
        with self._lock:
            while self._events and self._events[0] <= window_start:
                self._events.popleft()
            if len(self._events) >= self.max_messages_per_second:
                return False
            self._events.append(now)
            return True
