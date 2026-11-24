from datetime import UTC, datetime

import pytest
from vyro_controller.decide import ControllerConfig, decide
from vyro_controller.state import SystemState

TIMESTAMP = datetime(2026, 11, 20, 10, tzinfo=UTC)


def test_decide_holds_phase_during_minimum_green() -> None:
    state = SystemState("intersection-1", 0, 4.0, {}, TIMESTAMP)
    action = decide(state, ControllerConfig((0, 1), 5.0), {0: 1.0, 1: 10.0})

    assert action.phase_id == 0
    assert action.reason == "minimum_green"


def test_decide_selects_highest_admissible_pressure() -> None:
    state = SystemState("intersection-1", 0, 5.0, {}, TIMESTAMP)
    action = decide(state, ControllerConfig((0, 1, 2), 5.0), {0: 2.0, 1: 8.0, 2: 3.0})

    assert action.phase_id == 1
    assert action.reason == "queue_pressure"


def test_decide_rejects_invalid_phase_and_pressure() -> None:
    state = SystemState("intersection-1", 9, 5.0, {}, TIMESTAMP)
    with pytest.raises(ValueError, match="valid controller phase"):
        decide(state, ControllerConfig((0, 1), 5.0), {0: 1.0, 1: 2.0})

    valid_state = SystemState("intersection-1", 0, 5.0, {}, TIMESTAMP)
    with pytest.raises(ValueError, match="finite numbers"):
        decide(valid_state, ControllerConfig((0, 1), 5.0), {0: float("inf")})


def test_decide_uses_stale_state_fallback() -> None:
    state = SystemState("intersection-1", 1, 20.0, {}, TIMESTAMP)
    action = decide(state, ControllerConfig((0, 1), 5.0), {0: 10.0, 1: 1.0}, stale=True)

    assert action.phase_id == 1
    assert action.reason == "stale_state_fallback"


def test_controller_config_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        ControllerConfig(())
    with pytest.raises(ValueError, match="unique"):
        ControllerConfig((0, 0))
    with pytest.raises(ValueError, match="finite"):
        ControllerConfig((0, 1), float("nan"))
