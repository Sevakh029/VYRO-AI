"""SUMO-independent phase data converted for P2."""

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PhaseData:
    phase_id: int
    flow_veh_per_hour: float
    saturation_flow_veh_per_hour: float
    minimum_green_s: float
    clearance_s: float


def phases_from_sumolib_program(program: Any) -> tuple[PhaseData, ...]:
    """Convert a sumolib static program into plain dataclasses."""
    source_phases = program.getPhases()
    green_indexes = [
        index
        for index, phase in enumerate(source_phases)
        if ("G" in phase.state or "g" in phase.state)
        and "y" not in phase.state
        and "Y" not in phase.state
    ]
    phases = []
    for position, phase_index in enumerate(green_indexes):
        next_green_index = green_indexes[(position + 1) % len(green_indexes)]
        cursor = (phase_index + 1) % len(source_phases)
        clearance_s = 0.0
        while cursor != next_green_index:
            duration = source_phases[cursor].duration
            if not isinstance(duration, (int, float)) or not math.isfinite(duration):
                raise ValueError(f"SUMO phase {cursor} must have a finite duration")
            if duration < 0:
                raise ValueError(f"SUMO phase {cursor} duration must be non-negative")
            clearance_s += duration
            cursor = (cursor + 1) % len(source_phases)
        phases.append(
            PhaseData(
                phase_id=phase_index,
                flow_veh_per_hour=0.0,
                saturation_flow_veh_per_hour=1800.0,
                minimum_green_s=5.0,
                clearance_s=clearance_s,
            )
        )
    return tuple(phases)
