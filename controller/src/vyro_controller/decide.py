"""Pure-Python traffic phase decision helpers."""

from vyro_controller.state import Action, SystemState


def decide(state: SystemState) -> Action:
    """Keep the observed phase until a phase-selection policy is implemented."""
    return Action(
        intersection_id=state.intersection_id,
        phase_id=state.phase_id,
        reason="hold_current_phase",
        timestamp=state.timestamp,
        schema_version=state.schema_version,
    )
