"""Transport-independent controller state and action types."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime


def _validate_utc_timestamp(timestamp: datetime) -> None:
    if timestamp.tzinfo is None or timestamp.utcoffset() != UTC.utcoffset(timestamp):
        raise ValueError("timestamp must be timezone-aware UTC")


@dataclass(frozen=True)
class SystemState:
    """Observed state for one signalized intersection."""

    intersection_id: str
    phase_id: int
    time_in_phase_s: float
    detector_counts: dict[str, int]
    timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.intersection_id, str) or not self.intersection_id.strip():
            raise ValueError("intersection_id must not be empty")
        if (
            isinstance(self.phase_id, bool)
            or not isinstance(self.phase_id, int)
            or self.phase_id < 0
        ):
            raise ValueError("phase_id must be a non-negative integer")
        if (
            isinstance(self.time_in_phase_s, bool)
            or not isinstance(self.time_in_phase_s, (int, float))
            or not math.isfinite(self.time_in_phase_s)
        ):
            raise ValueError("time_in_phase_s must be finite")
        if self.time_in_phase_s < 0:
            raise ValueError("time_in_phase_s must be non-negative")
        if any(
            not isinstance(detector_id, str) or not detector_id.strip()
            for detector_id in self.detector_counts
        ):
            raise ValueError("detector IDs must not be empty")
        if any(type(count) is not int or count < 0 for count in self.detector_counts.values()):
            raise ValueError("detector counts must be non-negative integers")
        _validate_utc_timestamp(self.timestamp)


@dataclass(frozen=True)
class Action:
    """A phase command for one signalized intersection."""

    intersection_id: str
    phase_id: int
    reason: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.intersection_id, str) or not self.intersection_id.strip():
            raise ValueError("intersection_id must not be empty")
        if (
            isinstance(self.phase_id, bool)
            or not isinstance(self.phase_id, int)
            or self.phase_id < 0
        ):
            raise ValueError("phase_id must be a non-negative integer")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty")
        _validate_utc_timestamp(self.timestamp)
