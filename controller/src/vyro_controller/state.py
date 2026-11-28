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
    schema_version: str = "0.2"

    def __post_init__(self) -> None:
        if not isinstance(self.intersection_id, str) or not self.intersection_id.strip():
            raise ValueError("intersection_id must not be empty")
        intersection_id = self.intersection_id.strip()
        if len(intersection_id) > 128:
            raise ValueError("intersection_id must be at most 128 characters")
        object.__setattr__(self, "intersection_id", intersection_id)
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
        normalized_counts: dict[str, int] = {}
        for detector_id, count in self.detector_counts.items():
            if not isinstance(detector_id, str) or not detector_id.strip():
                raise ValueError("detector IDs must not be empty")
            normalized_id = detector_id.strip()
            if normalized_id in normalized_counts:
                raise ValueError("detector IDs must remain unique after whitespace trimming")
            if type(count) is not int or count < 0:
                raise ValueError("detector counts must be non-negative integers")
            normalized_counts[normalized_id] = count
        object.__setattr__(self, "detector_counts", normalized_counts)
        _validate_utc_timestamp(self.timestamp)


@dataclass(frozen=True)
class Action:
    """A phase command for one signalized intersection."""

    intersection_id: str
    phase_id: int
    reason: str
    timestamp: datetime
    schema_version: str = "0.2"
    command_id: str | None = None
    hold_s: float = 15.0

    def __post_init__(self) -> None:
        if not isinstance(self.intersection_id, str) or not self.intersection_id.strip():
            raise ValueError("intersection_id must not be empty")
        intersection_id = self.intersection_id.strip()
        if len(intersection_id) > 128:
            raise ValueError("intersection_id must be at most 128 characters")
        object.__setattr__(self, "intersection_id", intersection_id)
        if (
            isinstance(self.phase_id, bool)
            or not isinstance(self.phase_id, int)
            or self.phase_id < 0
        ):
            raise ValueError("phase_id must be a non-negative integer")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty")
        reason = self.reason.strip()
        if len(reason) > 256:
            raise ValueError("reason must be at most 256 characters")
        object.__setattr__(self, "reason", reason)
        _validate_utc_timestamp(self.timestamp)
        if (
            isinstance(self.hold_s, bool)
            or not isinstance(self.hold_s, (int, float))
            or not math.isfinite(self.hold_s)
            or self.hold_s <= 0
        ):
            raise ValueError("hold_s must be a finite positive duration")
        object.__setattr__(self, "hold_s", float(self.hold_s))
        if self.command_id is not None:
            if not isinstance(self.command_id, str) or not self.command_id.strip():
                raise ValueError("command_id must not be empty")
            if len(self.command_id) > 128:
                raise ValueError("command_id must be at most 128 characters")
