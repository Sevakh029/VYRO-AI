"""Pure, safety-constrained traffic phase decision helpers."""

import math
from dataclasses import dataclass

from vyro_controller.state import Action, SystemState


@dataclass(frozen=True)
class ControllerConfig:
    """Trusted phase configuration used to constrain controller decisions."""

    valid_phase_ids: tuple[int, ...]
    minimum_green_s: float = 5.0

    def __post_init__(self) -> None:
        if not self.valid_phase_ids:
            raise ValueError("valid_phase_ids must not be empty")
        if len(set(self.valid_phase_ids)) != len(self.valid_phase_ids):
            raise ValueError("valid phase IDs must be unique")
        if any(
            isinstance(phase_id, bool)
            or not isinstance(phase_id, int)
            or phase_id < 0
            for phase_id in self.valid_phase_ids
        ):
            raise ValueError("valid phase IDs must be non-negative integers")
        if isinstance(self.minimum_green_s, bool) or not isinstance(
            self.minimum_green_s, (int, float)
        ):
            raise ValueError("minimum_green_s must be numeric")
        if not math.isfinite(self.minimum_green_s):
            raise ValueError("minimum_green_s must be finite")
        if self.minimum_green_s < 0:
            raise ValueError("minimum_green_s must be non-negative")


def decide(
    state: SystemState,
    config: ControllerConfig | None = None,
    pressure_by_phase: dict[int, float] | None = None,
    *,
    stale: bool = False,
) -> Action:
    """Keep the current phase during minimum green, otherwise choose max pressure."""
    if config is None:
        config = ControllerConfig(valid_phase_ids=(state.phase_id,), minimum_green_s=0.0)

    if state.phase_id not in config.valid_phase_ids:
        raise ValueError("state phase_id is not a valid controller phase")

    selected_phase_id = state.phase_id
    if not stale and state.time_in_phase_s >= config.minimum_green_s:
        pressures = pressure_by_phase or {}
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in pressures.values()
        ):
            raise ValueError("phase pressures must be finite numbers")
        admissible_pressures = {
            phase_id: pressures.get(phase_id, 0.0)
            for phase_id in config.valid_phase_ids
        }
        selected_phase_id = max(
            admissible_pressures,
            key=lambda phase_id: (admissible_pressures[phase_id], -phase_id),
        )

    return Action(
        intersection_id=state.intersection_id,
        phase_id=selected_phase_id,
        reason=(
            "stale_state_fallback"
            if stale
            else "minimum_green"
            if selected_phase_id == state.phase_id
            else "queue_pressure"
        ),
        timestamp=state.timestamp,
        schema_version=state.schema_version,
    )
