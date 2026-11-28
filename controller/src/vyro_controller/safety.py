"""Pure-Python safety validation for controller actions."""

from collections.abc import Mapping
from dataclasses import dataclass

from .state import Action, SystemState


@dataclass(frozen=True)
class PhaseSafety:
    phase: int
    kind: str
    minimum_green_s: float
    yellow_s: float
    all_red_s: float


@dataclass(frozen=True)
class SignalSafety:
    signal_id: str
    phases: tuple[PhaseSafety, ...]
    yellow_phase: int
    all_red_phase: int
    max_wait_s: float


@dataclass(frozen=True)
class SafetyDecision:
    accepted: bool
    reason: str


def signal_safety_from_dict(raw: Mapping[str, object]) -> SignalSafety:
    signal_id = raw.get("signal_id")
    if not isinstance(signal_id, str) or not signal_id.strip():
        raise ValueError("signal_id must not be empty")
    raw_phases = raw.get("phases")
    if not isinstance(raw_phases, list) or not raw_phases:
        raise ValueError(f"signal {signal_id} must define phases")

    phases: list[PhaseSafety] = []
    for item in raw_phases:
        if not isinstance(item, Mapping):
            raise ValueError(f"signal {signal_id} has an invalid phase")
        phase = item.get("phase")
        kind = item.get("kind")
        minimum = item.get("minimum_green_s")
        yellow = item.get("yellow_s")
        all_red = item.get("all_red_s")
        if isinstance(phase, bool) or not isinstance(phase, int) or phase < 0:
            raise ValueError(f"signal {signal_id} has an invalid phase index")
        if kind not in {"green", "yellow", "all_red"}:
            raise ValueError(f"signal {signal_id} has an invalid phase kind")
        values = (minimum, yellow, all_red)
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise ValueError(f"signal {signal_id} phase {phase} has invalid timing")
        if min(float(minimum), float(yellow), float(all_red)) < 0:
            raise ValueError(f"signal {signal_id} phase {phase} has negative timing")
        phases.append(
            PhaseSafety(
                phase=phase,
                kind=str(kind),
                minimum_green_s=float(minimum),
                yellow_s=float(yellow),
                all_red_s=float(all_red),
            )
        )
    if len({phase.phase for phase in phases}) != len(phases):
        raise ValueError(f"signal {signal_id} has duplicate phase indices")

    yellow = raw.get("yellow_phase")
    all_red = raw.get("all_red_phase")
    max_wait = raw.get("max_wait_s")
    if isinstance(yellow, bool) or not isinstance(yellow, int):
        raise ValueError(f"signal {signal_id} has an invalid yellow phase")
    if isinstance(all_red, bool) or not isinstance(all_red, int):
        raise ValueError(f"signal {signal_id} has an invalid all-red phase")
    if isinstance(max_wait, bool) or not isinstance(max_wait, (int, float)) or float(max_wait) <= 0:
        raise ValueError(f"signal {signal_id} has an invalid max_wait_s")

    allowed_indexes = {phase.phase for phase in phases}
    if yellow not in allowed_indexes or all_red not in allowed_indexes:
        raise ValueError(f"signal {signal_id} clearance phases are not configured")

    return SignalSafety(
        signal_id=signal_id,
        phases=tuple(phases),
        yellow_phase=yellow,
        all_red_phase=all_red,
        max_wait_s=float(max_wait),
    )


def validate_action(
    action: Action,
    state: SystemState,
    config: SignalSafety,
) -> SafetyDecision:
    if action.intersection_id != config.signal_id:
        return SafetyDecision(False, "action signal_id does not match trusted signal configuration")
    phase_by_index = {phase.phase: phase for phase in config.phases}
    if action.phase_id not in phase_by_index:
        return SafetyDecision(False, "phase is not configured for this signal")

    target = phase_by_index[action.phase_id]
    current = phase_by_index.get(state.phase_id)
    if current is None:
        return SafetyDecision(False, "current phase is not configured for this signal")
    if action.phase_id == state.phase_id:
        if target.kind == "green" and state.time_in_phase_s > config.max_wait_s:
            return SafetyDecision(False, "maximum waiting constraint exceeded")
        return SafetyDecision(True, "hold current phase")

    if current.kind == "green" and state.time_in_phase_s < current.minimum_green_s:
        return SafetyDecision(False, "minimum green time has not elapsed")
    if target.kind == "green":
        if state.phase_id != config.all_red_phase:
            return SafetyDecision(False, "green change requires yellow and all-red clearance")
    if target.kind == "yellow" and current.kind == "green":
        return SafetyDecision(True, "yellow transition approved")
    if target.kind == "all_red":
        if state.phase_id != config.yellow_phase:
            return SafetyDecision(False, "all-red requires preceding yellow transition")
        if state.time_in_phase_s < phase_by_index[config.yellow_phase].yellow_s:
            return SafetyDecision(False, "yellow clearance duration not elapsed")
        return SafetyDecision(True, "all-red transition approved")
    if target.kind == "green":
        if state.time_in_phase_s < current.minimum_green_s:
            return SafetyDecision(False, "all-red clearance duration not elapsed")
        return SafetyDecision(True, "green action approved after clearance")
    return SafetyDecision(False, "unsupported unsafe phase transition")
