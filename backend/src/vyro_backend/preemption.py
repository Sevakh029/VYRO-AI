import threading
from datetime import UTC, datetime

from .schemas import PreemptionRequest


class PreemptionCoordinator:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests: dict[str, PreemptionRequest] = {}

    def request(
        self,
        intersection_id: str,
        vehicle_id: str,
        lead_time_s: float,
    ) -> PreemptionRequest:
        if lead_time_s <= 0:
            raise ValueError("lead_time_s must be positive")
        request = PreemptionRequest(
            intersection_id=intersection_id,
            vehicle_id=vehicle_id,
            lead_time_s=lead_time_s,
            state="requested",
            timestamp=datetime.now(UTC),
        )
        with self._lock:
            self.requests[vehicle_id] = request
        return request

    def grant(self, vehicle_id: str) -> PreemptionRequest:
        with self._lock:
            request = self.requests.get(vehicle_id)
            if request is None:
                raise KeyError(vehicle_id)
            granted = request.model_copy(update={"state": "granted"})
            self.requests[vehicle_id] = granted
            return granted

    def clear(self, vehicle_id: str) -> PreemptionRequest:
        with self._lock:
            request = self.requests.get(vehicle_id)
            if request is None:
                raise KeyError(vehicle_id)
            cleared = request.model_copy(update={"state": "cleared"})
            self.requests[vehicle_id] = cleared
            return cleared
