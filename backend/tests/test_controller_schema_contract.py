from dataclasses import asdict, fields
from datetime import UTC, datetime, timedelta

from vyro_backend.adapters import (
    action_to_command,
    command_to_action,
    intersection_to_state,
    state_to_intersection,
)
from vyro_backend.schemas import IntersectionState, SignalCommand
from vyro_controller.decide import decide
from vyro_controller.state import Action, SystemState
from vyro_controller.types import parse_signals_config


def test_controller_state_and_action_match_v02_message_shapes() -> None:
    assert tuple(field.name for field in fields(SystemState)) == tuple(
        IntersectionState.model_fields
    )
    assert "intersection_id" in tuple(field.name for field in fields(Action))
    assert "phase_id" in tuple(field.name for field in fields(Action))

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
            "command_id": "command-1",
            "signal_id": "signal-1",
            "phase": 1,
            "hold_s": 15.0,
            "reason": "queue_pressure",
            "ts_utc": "2026-11-20T10:00:00Z",
        }
    )

    assert asdict(SystemState(**state_message.model_dump())) == state_message.model_dump()
    action = command_to_action(command_message)
    assert action.intersection_id == "signal-1"
    assert action.phase_id == 1


def test_schema_controller_adapters_round_trip_utc_messages() -> None:
    timestamp = datetime(2026, 11, 24, 10, tzinfo=UTC)
    state_message = IntersectionState(
        intersection_id="intersection-1",
        phase_id=2,
        time_in_phase_s=15.5,
        detector_counts={"north": 4},
        timestamp=timestamp,
        schema_version="0.3",
    )
    command_message = SignalCommand(
        command_id="command-1",
        signal_id="signal-1",
        phase=1,
        hold_s=15.0,
        reason="queue pressure",
        ts_utc=timestamp,
        schema_version="0.3",
    )

    state = intersection_to_state(state_message)
    action = command_to_action(command_message)

    assert state_to_intersection(state) == state_message
    round_trip = action_to_command(action)
    assert round_trip.signal_id == command_message.signal_id
    assert round_trip.phase == command_message.phase
    assert round_trip.hold_s == 15.0
    assert state.timestamp.utcoffset() == timedelta(0)
    assert action.timestamp.utcoffset() == timedelta(0)


def test_backend_intersection_adapter_feeds_pressure_controller() -> None:
    timestamp = datetime(2026, 11, 24, 10, tzinfo=UTC)
    message = IntersectionState(
        intersection_id="intersection-1",
        phase_id=0,
        time_in_phase_s=25,
        detector_counts={"north": 1, "east": 8},
        timestamp=timestamp,
    )
    config = parse_signals_config(
        {
            "signals": {
                "intersection-1": {
                    "phases": {
                        "0": {
                            "min_green_s": 10,
                            "detectors": ["north"],
                            "allowed_next": [1],
                        },
                        "1": {
                            "min_green_s": 10,
                            "detectors": ["east"],
                            "allowed_next": [0],
                        },
                    }
                }
            }
        }
    )

    actions = decide(intersection_to_state(message), config)

    assert len(actions) == 1
    assert actions[0].signal_id == message.intersection_id
    assert actions[0].phase == 1
