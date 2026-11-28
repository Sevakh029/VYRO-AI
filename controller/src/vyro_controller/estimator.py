"""Queue estimates from detector counts and privacy-preserving probe observations."""

import math
from collections.abc import Iterable
from dataclasses import dataclass, replace

from vyro_controller.state import SystemState


@dataclass(frozen=True)
class ProbeVehicle:
    """Map-matched probe observation relative to an approach stop line."""

    approach_id: str
    distance_to_stop_line_m: float
    speed_mps: float

    def __post_init__(self) -> None:
        if not isinstance(self.approach_id, str) or not self.approach_id.strip():
            raise ValueError("approach_id must not be empty")
        object.__setattr__(self, "approach_id", self.approach_id.strip())
        for name, value in (
            ("distance_to_stop_line_m", self.distance_to_stop_line_m),
            ("speed_mps", self.speed_mps),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError(f"{name} must be finite and non-negative")


def estimate_queues(
    state: SystemState,
    probe_vehicles: Iterable[ProbeVehicle] = (),
    *,
    near_stop_line_m: float = 50.0,
    queued_speed_mps: float = 0.5,
) -> dict[str, int]:
    """Fuse per-approach counts with stopped probes near each stop line.

    The larger of the detector count and qualifying probe count is used to
    avoid counting the same traffic twice when both sources observe it.
    """
    for name, value in (
        ("near_stop_line_m", near_stop_line_m),
        ("queued_speed_mps", queued_speed_mps),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"{name} must be finite and non-negative")

    estimates = dict(state.detector_counts)
    probe_counts: dict[str, int] = {}
    for vehicle in probe_vehicles:
        if (
            vehicle.distance_to_stop_line_m <= near_stop_line_m
            and vehicle.speed_mps <= queued_speed_mps
        ):
            probe_counts[vehicle.approach_id] = (
                probe_counts.get(vehicle.approach_id, 0) + 1
            )

    for approach_id, probe_count in probe_counts.items():
        estimates[approach_id] = max(estimates.get(approach_id, 0), probe_count)
    return estimates


def estimate_state(
    state: SystemState,
    probe_vehicles: Iterable[ProbeVehicle] = (),
    *,
    near_stop_line_m: float = 50.0,
    queued_speed_mps: float = 0.5,
) -> SystemState:
    """Return a controller state with fused per-approach queue estimates."""
    return replace(
        state,
        detector_counts=estimate_queues(
            state,
            probe_vehicles,
            near_stop_line_m=near_stop_line_m,
            queued_speed_mps=queued_speed_mps,
        ),
    )
