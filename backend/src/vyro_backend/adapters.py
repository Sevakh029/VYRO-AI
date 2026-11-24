"""Adapters between authoritative Pydantic schemas and pure controller dataclasses."""

from vyro_controller.state import Action, SystemState

from .schemas import IntersectionState, SignalCommand


def intersection_to_state(message: IntersectionState) -> SystemState:
    return SystemState(
        intersection_id=message.intersection_id,
        phase_id=message.phase_id,
        time_in_phase_s=message.time_in_phase_s,
        detector_counts=message.detector_counts,
        timestamp=message.timestamp,
        schema_version=message.schema_version,
    )


def state_to_intersection(state: SystemState) -> IntersectionState:
    return IntersectionState(
        intersection_id=state.intersection_id,
        phase_id=state.phase_id,
        time_in_phase_s=state.time_in_phase_s,
        detector_counts=state.detector_counts,
        timestamp=state.timestamp,
        schema_version=state.schema_version,
    )


def command_to_action(message: SignalCommand) -> Action:
    return Action(
        intersection_id=message.intersection_id,
        phase_id=message.phase_id,
        reason=message.reason,
        timestamp=message.timestamp,
        schema_version=message.schema_version,
        command_id=message.command_id,
    )


def action_to_command(action: Action) -> SignalCommand:
    return SignalCommand(
        intersection_id=action.intersection_id,
        phase_id=action.phase_id,
        reason=action.reason,
        timestamp=action.timestamp,
        schema_version=action.schema_version,
        command_id=action.command_id,
    )
