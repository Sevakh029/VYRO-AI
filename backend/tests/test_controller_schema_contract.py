from dataclasses import asdict, fields

from vyro_backend.schemas import IntersectionState, SignalCommand
from vyro_controller.state import Action, SystemState


def test_controller_state_and_action_match_v01_message_shapes() -> None:
    assert tuple(field.name for field in fields(SystemState)) == tuple(
        IntersectionState.model_fields
    )
    assert tuple(field.name for field in fields(Action)) == tuple(SignalCommand.model_fields)

    state_message = IntersectionState.model_validate(
        {
            "intersection_id": "intersection-1",
            "phase_id": 2,
            "time_in_phase_s": 15.5,
            "detector_counts": {"approach_north": 4},
            "timestamp": "2026-11-20T10:00:00Z",
        }
    )
    command_message = SignalCommand.model_validate(
        {
            "intersection_id": "intersection-1",
            "phase_id": 1,
            "reason": "queue_pressure",
            "timestamp": "2026-11-20T10:00:00Z",
        }
    )

    assert asdict(SystemState(**state_message.model_dump())) == state_message.model_dump()
    assert asdict(Action(**command_message.model_dump())) == command_message.model_dump()
