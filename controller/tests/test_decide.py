from datetime import UTC, datetime

from vyro_controller import parse_signals_config
from vyro_controller.decide import decide
from vyro_controller.pressure import PressureController
from vyro_controller.state import SystemState
from vyro_controller.types import Action

TIMESTAMP = datetime(2026, 11, 20, 10, tzinfo=UTC)
SIGNALS = parse_signals_config(
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


def test_decide_holds_current_phase() -> None:
    state = SystemState("intersection-1", 2, 15.5, {"approach_north": 4}, TIMESTAMP)

    assert decide(state) == []


def test_decide_returns_safe_pressure_action() -> None:
    state = SystemState(
        "intersection-1",
        0,
        12,
        {"north": 1, "east": 8},
        TIMESTAMP,
    )

    actions = decide(state, SIGNALS)

    assert len(actions) == 1
    assert isinstance(actions[0], Action)
    assert actions[0].phase == 1
    assert actions[0].reason == "queue_pressure"
    assert actions[0].hold_s == 10


def test_decide_rechecks_pressure_action_and_holds_on_unsafe_switch(monkeypatch) -> None:
    state = SystemState("intersection-1", 0, 5, {"east": 8}, TIMESTAMP)
    monkeypatch.setattr(
        PressureController,
        "decide",
        lambda *_: [Action("intersection-1", 1, 15, "queue_pressure")],
    )

    actions = decide(state, SIGNALS)

    assert len(actions) == 1
    assert actions[0].phase == state.phase_id
    assert actions[0].hold_s == 5
    assert actions[0].reason == "hold_current_phase"


def test_decide_emits_no_action_for_unconfigured_observed_phase() -> None:
    state = SystemState("intersection-1", 9, 20, {"east": 8}, TIMESTAMP)

    assert decide(state, SIGNALS) == []
