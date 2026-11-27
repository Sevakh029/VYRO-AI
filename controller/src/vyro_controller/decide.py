"""Pure-Python traffic phase decision helpers."""

from typing import Any

from vyro_controller.pressure import PressureController
from vyro_controller.state import SystemState
from vyro_controller.types import Action, SignalConfig


def decide(
    state: SystemState | dict[str, Any],
    config: SignalConfig | dict[str, SignalConfig] | None = None,
    switching_penalty: float = 0.0,
) -> list[Action]:
    """Select one requested phase using the pressure policy for mock states."""
    if config is None:
        return []
    if isinstance(config, SignalConfig):
        signal_id = (
            state.intersection_id
            if isinstance(state, SystemState)
            else str(state.get("signal_id", state.get("intersection_id", "")))
        )
        signals = {signal_id: config}
    else:
        signals = config
    return PressureController(signals, switching_penalty).decide(state)
