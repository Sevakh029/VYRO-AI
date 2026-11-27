"""Pure safety checks for configured signal phases."""

from vyro_controller.types import PhaseConfig, SignalConfig


def allowed_phases(signal: SignalConfig) -> tuple[int, ...]:
    """Return the complete set of configured valid phase IDs."""
    return tuple(phase.phase for phase in signal.phases)


def is_allowed_phase(signal: SignalConfig, phase: int) -> bool:
    return phase in allowed_phases(signal)


def min_green_met(time_in_phase_s: float, min_green_s: float) -> bool:
    if time_in_phase_s < 0 or min_green_s < 0:
        raise ValueError("durations must be non-negative")
    return time_in_phase_s >= min_green_s


def can_switch(
    signal: SignalConfig,
    current_phase: int,
    target_phase: int,
    time_in_phase_s: float,
) -> bool:
    """Check valid phase, minimum-green, and configured transition constraints."""
    if not is_allowed_phase(signal, target_phase):
        return False
    current = next((phase for phase in signal.phases if phase.phase == current_phase), None)
    if current is None:
        return False
    if not min_green_met(time_in_phase_s, current.min_green_s):
        return False
    if current.allowed_next is not None:
        return target_phase in current.allowed_next
    return True


def clearance_for_transition(
    signal: SignalConfig,
    current_phase: int,
) -> tuple[float, float]:
    """Return (yellow_s, all_red_s) for a configured source phase."""
    current = next((phase for phase in signal.phases if phase.phase == current_phase), None)
    if current is None:
        raise ValueError(f"unknown phase {current_phase} for signal {signal.signal_id}")
    return current.yellow_s, current.all_red_s


def yellow_all_red(
    signal: SignalConfig,
    from_phase: int,
    to_phase: int,
) -> tuple[float, float]:
    del to_phase
    return clearance_for_transition(signal, from_phase)


def max_wait_exceeded(wait_s: float, max_wait_s: float) -> bool:
    if wait_s < 0 or max_wait_s < 0:
        raise ValueError("durations must be non-negative")
    return wait_s >= max_wait_s


def apply_safety(
    signal: SignalConfig,
    requested_phase: int,
    current_phase: int,
    time_in_phase_s: float,
) -> int:
    """Return the requested phase only when all basic safety checks pass."""
    if not can_switch(signal, current_phase, requested_phase, time_in_phase_s):
        return current_phase
    return requested_phase


def phase_config(signal: SignalConfig, phase: int) -> PhaseConfig:
    for config in signal.phases:
        if config.phase == phase:
            return config
    raise ValueError(f"unknown phase {phase} for signal {signal.signal_id}")


get_allowed_phases = allowed_phases
minimum_green_met = min_green_met
