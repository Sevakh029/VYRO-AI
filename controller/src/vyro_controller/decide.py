"""Pure-Python traffic phase decision helpers."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from vyro_controller.pressure import PressureController
from vyro_controller.safety import apply_safety, is_allowed_phase
from vyro_controller.state import SystemState
from vyro_controller.types import Action, SignalConfig


def _as_system_state(state: SystemState | Mapping[str, Any]) -> SystemState:
    if isinstance(state, SystemState):
        return state

    timestamp = state.get("timestamp", datetime.now(UTC))
    if not isinstance(timestamp, datetime):
        raise ValueError("state timestamp must be a datetime")
    raw_counts = state.get("detector_counts", state.get("queues", {}))
    if not isinstance(raw_counts, Mapping):
        raise ValueError("detector_counts/queues must be a mapping")
    counts: dict[str, int] = {}
    for approach_id, count in raw_counts.items():
        if not isinstance(approach_id, str) or type(count) is not int:
            raise ValueError("detector counts must map string IDs to integers")
        counts[approach_id] = count

    return SystemState(
        intersection_id=state.get("signal_id", state.get("intersection_id", "")),
        phase_id=state.get("phase_id", state.get("phase", 0)),
        time_in_phase_s=state.get(
            "time_in_phase_s", state.get("elapsed_s", 0)
        ),
        detector_counts=counts,
        timestamp=timestamp,
        schema_version=state.get("schema_version", "0.2"),
    )


def decide(
    state: SystemState | Mapping[str, Any],
    config: SignalConfig | dict[str, SignalConfig] | None = None,
    switching_penalty: float = 0.0,
) -> list[Action]:
    """Select a pressure phase and pass every returned action through safety."""
    if config is None:
        return []
    system_state = _as_system_state(state)
    if isinstance(config, SignalConfig):
        signals = {system_state.intersection_id: config}
    else:
        signals = config

    signal = signals.get(system_state.intersection_id)
    if signal is None or not is_allowed_phase(signal, system_state.phase_id):
        return []

    candidates = PressureController(signals, switching_penalty).decide(system_state)
    actions: list[Action] = []
    for candidate in candidates:
        if candidate.signal_id != system_state.intersection_id:
            continue
        safe_phase = apply_safety(
            signal,
            candidate.phase,
            system_state.phase_id,
            system_state.time_in_phase_s,
        )
        if not is_allowed_phase(signal, safe_phase):
            continue
        phase = next(
            phase_config
            for phase_config in signal.phases
            if phase_config.phase == safe_phase
        )
        hold_s = (
            max(phase.min_green_s - system_state.time_in_phase_s, 0.001)
            if safe_phase == system_state.phase_id
            else max(phase.min_green_s, 0.001)
        )
        actions.append(
            Action(
                signal_id=system_state.intersection_id,
                phase=safe_phase,
                hold_s=hold_s,
                reason=(
                    candidate.reason
                    if safe_phase != system_state.phase_id
                    else "hold_current_phase"
                ),
            )
        )
    return actions
