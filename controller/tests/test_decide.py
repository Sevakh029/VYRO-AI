from datetime import UTC, datetime

from vyro_controller.decide import decide
from vyro_controller.state import SystemState

TIMESTAMP = datetime(2026, 11, 20, 10, tzinfo=UTC)


def test_decide_holds_current_phase() -> None:
    state = SystemState("intersection-1", 2, 15.5, {"approach_north": 4}, TIMESTAMP)

    assert decide(state) == []
