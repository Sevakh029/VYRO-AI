from vyro_controller.pressure import PressureController, weighted_queue_pressure
from vyro_controller.safety import (
    can_switch,
    max_wait_exceeded,
    yellow_all_red,
)
from vyro_controller.types import Action, parse_signals_config

SIGNALS = parse_signals_config(
    {
        "signals": {
            "intersection-1": {
                "phases": {
                    "0": {
                        "min_green_s": 20,
                        "yellow_s": 3,
                        "all_red_s": 2,
                        "detectors": ["north"],
                        "weight": 1,
                        "allowed_next": [1],
                    },
                    "1": {
                        "min_green_s": 20,
                        "yellow_s": 3,
                        "all_red_s": 2,
                        "detectors": ["east"],
                        "weight": 2,
                        "allowed_next": [0],
                    },
                }
            }
        }
    }
)


def test_action_contract_and_weighted_pressure() -> None:
    action = Action("intersection-1", 1, 20.0, "queue_pressure")
    assert action.phase == 1
    assert weighted_queue_pressure({"north": 4, "east": 2}, {"north": 1, "east": 3}) == 10


def test_pressure_controller_switches_to_higher_weighted_phase() -> None:
    controller = PressureController(SIGNALS, switching_penalty=1)
    actions = controller.decide(
        {
            "signal_id": "intersection-1",
            "phase": 0,
            "time_in_phase_s": 25,
            "queues": {"north": 1, "east": 8},
        }
    )
    assert len(actions) == 1
    assert actions[0].phase == 1
    assert actions[0].reason == "queue_pressure"


def test_safety_blocks_switch_before_minimum_green() -> None:
    signal = SIGNALS["intersection-1"]
    assert can_switch(signal, 0, 1, 19) is False
    assert can_switch(signal, 0, 1, 20) is True
    assert yellow_all_red(signal, 0, 1) == (3.0, 2.0)
    assert max_wait_exceeded(30, 30) is True
