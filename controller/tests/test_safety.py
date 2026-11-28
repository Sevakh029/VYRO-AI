from datetime import UTC, datetime

from vyro_controller.safety import signal_safety_from_dict, validate_action
from vyro_controller.state import Action, SystemState

TIMESTAMP = datetime(2026, 11, 20, 10, tzinfo=UTC)


def config() -> object:
    return signal_safety_from_dict(
        {
            "signal_id": "signal-1",
            "phases": [
                {"phase": 0, "kind": "green", "minimum_green_s": 20, "yellow_s": 0, "all_red_s": 0},
                {"phase": 1, "kind": "yellow", "minimum_green_s": 4, "yellow_s": 4, "all_red_s": 0},
                {
                    "phase": 2,
                    "kind": "all_red",
                    "minimum_green_s": 5,
                    "yellow_s": 0,
                    "all_red_s": 5,
                },
            ],
            "yellow_phase": 1,
            "all_red_phase": 2,
            "max_wait_s": 120,
        }
    )


def test_unknown_phase_is_rejected() -> None:
    state = SystemState("signal-1", 0, 30, {}, TIMESTAMP)
    action = Action("signal-1", 99, "change", TIMESTAMP)
    decision = validate_action(action, state, config())
    assert not decision.accepted
    assert "not configured" in decision.reason


def test_minimum_green_blocks_switch() -> None:
    state = SystemState("signal-1", 0, 10, {}, TIMESTAMP)
    action = Action("signal-1", 1, "yellow", TIMESTAMP)
    decision = validate_action(action, state, config())
    assert not decision.accepted
    assert "minimum green" in decision.reason


def test_yellow_all_red_sequence_is_required() -> None:
    state = SystemState("signal-1", 0, 30, {}, TIMESTAMP)
    signal_config = config()
    decision = validate_action(
        Action("signal-1", 1, "yellow", TIMESTAMP),
        state,
        signal_config,
    )
    assert decision.accepted
    yellow = SystemState("signal-1", 1, 4, {}, TIMESTAMP)
    decision = validate_action(
        Action("signal-1", 2, "all red", TIMESTAMP),
        yellow,
        signal_config,
    )
    assert decision.accepted


def test_direct_green_change_requires_clearance() -> None:
    state = SystemState("signal-1", 0, 30, {}, TIMESTAMP)
    decision = validate_action(Action("signal-1", 0, "hold", TIMESTAMP), state, config())
    assert decision.accepted

    direct = validate_action(Action("signal-1", 0, "change", TIMESTAMP), state, config())
    assert direct.accepted
