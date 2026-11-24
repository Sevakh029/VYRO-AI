"""Pure Webster fixed-time signal timing calculations."""

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseFlow:
    """Critical approach demand and timing constraints for a signal phase."""

    phase_id: int
    flow_veh_per_hour: float
    saturation_flow_veh_per_hour: float
    minimum_green_s: float = 5.0
    clearance_s: float = 0.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.phase_id, bool)
            or not isinstance(self.phase_id, int)
            or self.phase_id < 0
        ):
            raise ValueError("phase_id must be a non-negative integer")
        for name, value in (
            ("flow_veh_per_hour", self.flow_veh_per_hour),
            ("saturation_flow_veh_per_hour", self.saturation_flow_veh_per_hour),
            ("minimum_green_s", self.minimum_green_s),
            ("clearance_s", self.clearance_s),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(f"{name} must be finite")
        if self.flow_veh_per_hour < 0:
            raise ValueError("flow_veh_per_hour must be non-negative")
        if self.saturation_flow_veh_per_hour <= 0:
            raise ValueError("saturation_flow_veh_per_hour must be positive")
        if self.minimum_green_s <= 0:
            raise ValueError("minimum_green_s must be positive")
        if self.clearance_s < 0:
            raise ValueError("clearance_s must be non-negative")


@dataclass(frozen=True)
class GreenSplit:
    phase_id: int
    green_s: float


@dataclass(frozen=True)
class WebsterPlan:
    cycle_length_s: float
    lost_time_s: float
    green_splits: tuple[GreenSplit, ...]
    oversaturated: bool


def calculate_webster_plan(
    phases: Sequence[PhaseFlow],
    *,
    min_cycle_s: float = 30.0,
    max_cycle_s: float = 120.0,
) -> WebsterPlan:
    """Calculate a bounded Webster cycle and safe minimum-constrained green splits."""
    if not phases:
        raise ValueError("at least one phase is required")
    if len({phase.phase_id for phase in phases}) != len(phases):
        raise ValueError("phase IDs must be unique")
    for name, value in (("min_cycle_s", min_cycle_s), ("max_cycle_s", max_cycle_s)):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"{name} must be finite and positive")
    if max_cycle_s < min_cycle_s:
        raise ValueError("max_cycle_s must be greater than or equal to min_cycle_s")

    lost_time_s = sum(phase.clearance_s for phase in phases)
    minimum_green_total_s = sum(phase.minimum_green_s for phase in phases)
    if not math.isfinite(lost_time_s) or not math.isfinite(minimum_green_total_s):
        raise ValueError("summed phase timings must be finite")
    if minimum_green_total_s + lost_time_s > max_cycle_s:
        raise ValueError("minimum greens and clearance exceed max_cycle_s")

    ratios = tuple(
        phase.flow_veh_per_hour / phase.saturation_flow_veh_per_hour for phase in phases
    )
    critical_flow_ratio = sum(ratios)
    if not math.isfinite(critical_flow_ratio):
        raise ValueError("summed critical flow ratios must be finite")
    oversaturated = critical_flow_ratio >= 1.0
    if oversaturated:
        cycle_length_s = max_cycle_s
    else:
        cycle_length_s = (1.5 * lost_time_s + 5.0) / (1.0 - critical_flow_ratio)
        cycle_length_s = min(max(cycle_length_s, min_cycle_s), max_cycle_s)

    cycle_length_s = max(cycle_length_s, minimum_green_total_s + lost_time_s)
    available_green_s = cycle_length_s - lost_time_s
    weights = ratios if critical_flow_ratio > 0 else tuple(1.0 for _ in phases)
    remaining_phase_indexes = set(range(len(phases)))
    green_times = [0.0] * len(phases)
    remaining_green_s = available_green_s
    while remaining_phase_indexes:
        total_weight = sum(weights[index] for index in remaining_phase_indexes)
        if total_weight == 0:
            active_weights = {index: 1.0 for index in remaining_phase_indexes}
            total_weight = float(len(remaining_phase_indexes))
        else:
            active_weights = {index: weights[index] for index in remaining_phase_indexes}
        proposed = {
            index: remaining_green_s * (active_weights[index] / total_weight)
            for index in remaining_phase_indexes
        }
        constrained = [
            index
            for index, green_s in proposed.items()
            if green_s < phases[index].minimum_green_s
        ]
        if not constrained:
            for index, green_s in proposed.items():
                green_times[index] = green_s
            break
        for index in constrained:
            minimum_green_s = phases[index].minimum_green_s
            green_times[index] = minimum_green_s
            remaining_green_s -= minimum_green_s
            remaining_phase_indexes.remove(index)

    green_times[-1] += available_green_s - sum(green_times)

    return WebsterPlan(
        cycle_length_s=cycle_length_s,
        lost_time_s=lost_time_s,
        green_splits=tuple(
            GreenSplit(phase.phase_id, green_s)
            for phase, green_s in zip(phases, green_times, strict=True)
        ),
        oversaturated=oversaturated,
    )
