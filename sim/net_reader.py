"""SUMO-independent phase data converted for P2."""

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
    phases = []
    for index, phase in enumerate(program.getPhases()):
        state = phase.state
        if "G" not in state and "g" not in state:
            continue
        phases.append(
            PhaseData(
                phase_id=index,
                flow_veh_per_hour=0.0,
                saturation_flow_veh_per_hour=1800.0,
                minimum_green_s=5.0,
                clearance_s=0.0,
            )
        )
    return tuple(phases)
