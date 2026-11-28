"""Pressure-based phase selection for mock and live aggregated states."""

from collections.abc import Mapping, Sequence
from typing import Any

from vyro_controller.safety import apply_safety
from vyro_controller.state import SystemState
from vyro_controller.types import Action, SignalConfig


def weighted_queue_pressure(
    detector_counts: Mapping[str, int],
    weights: Mapping[str, float] | None = None,
    phase_detector_ids: Sequence[str] = (),
) -> float:
    """Sum weighted queue counts, optionally restricted to a phase's detectors."""
    selected = detector_counts if not phase_detector_ids else {
        detector_id: detector_counts.get(detector_id, 0)
        for detector_id in phase_detector_ids
    }
    pressure = 0.0
    for detector_id, count in selected.items():
        weight = 1.0 if weights is None else weights.get(detector_id, 0.0)
        pressure += float(count) * float(weight)
    return pressure


def phase_pressure(
    phase: int,
    detector_counts: Mapping[str, int],
    detector_weights: Mapping[str, float] | None,
) -> float:
    del phase
    return weighted_queue_pressure(detector_counts, detector_weights)


class PressureController:
    """Select the highest-pressure admissible phase with a switching penalty."""

    def __init__(
        self,
        signals: Mapping[str, SignalConfig] | None = None,
        switching_penalty: float = 0.0,
    ) -> None:
        if switching_penalty < 0:
            raise ValueError("switching_penalty must be non-negative")
        self.signals = dict(signals or {})
        self.switching_penalty = switching_penalty

    def _state_values(self, state: Any) -> tuple[str, int, float, Mapping[str, int]]:
        if isinstance(state, SystemState):
            return (
                state.intersection_id,
                state.phase_id,
                state.time_in_phase_s,
                state.detector_counts,
            )
        if isinstance(state, Mapping):
            signal_id = str(state.get("signal_id", state.get("intersection_id", "")))
            phase = int(state.get("phase", state.get("phase_id", 0)))
            elapsed = float(state.get("time_in_phase_s", state.get("elapsed_s", 0)))
            counts = state.get("detector_counts", state.get("queues", {}))
            if not isinstance(counts, Mapping):
                raise ValueError("detector_counts/queues must be a mapping")
            return signal_id, phase, elapsed, counts
        raise ValueError("state must be a SystemState or mapping")

    def decide(self, state: Any) -> list[Action]:
        signal_id, current_phase, elapsed, counts = self._state_values(state)
        signal = self.signals.get(signal_id)
        if signal is None:
            return []
        if not any(phase.phase == current_phase for phase in signal.phases):
            return []

        scored: list[tuple[float, int]] = []
        for phase_config in signal.phases:
            pressure = weighted_queue_pressure(
                counts,
                None,
                phase_config.detector_ids,
            ) * phase_config.weight
            if phase_config.phase != current_phase:
                pressure -= self.switching_penalty
            scored.append((pressure, phase_config.phase))

        if not scored:
            return []
        target = max(scored, key=lambda item: (item[0], -item[1]))[1]
        target = apply_safety(signal, target, current_phase, elapsed)

        phase = next(config for config in signal.phases if config.phase == target)
        reason = "hold_current_phase" if target == current_phase else "queue_pressure"
        return [
            Action(
                signal_id=signal_id,
                phase=target,
                hold_s=(
                    max(phase.min_green_s - elapsed, 0.001)
                    if target == current_phase
                    else max(phase.min_green_s, 0.001)
                ),
                reason=reason,
            )
        ]
