from datetime import UTC, datetime, timedelta, timezone

import pytest
from vyro_controller.state import Action, SystemState


def test_state_and_action_accept_schema_shaped_utc_values() -> None:
    timestamp = datetime(2026, 11, 20, 10, tzinfo=UTC)
    state = SystemState(" intersection-1 ", 2, 15.5, {" approach_north ": 4}, timestamp)
    action = Action(" intersection-1 ", 1, " queue_pressure ", timestamp)

    assert state.intersection_id == "intersection-1"
    assert state.detector_counts == {"approach_north": 4}
    assert action.intersection_id == "intersection-1"
    assert action.phase_id == 1
    assert action.reason == "queue_pressure"


@pytest.mark.parametrize(
    "timestamp",
    [
        datetime(2026, 11, 20, 10),
        datetime(2026, 11, 20, 10, tzinfo=timezone(timedelta(hours=1))),
    ],
)
def test_state_rejects_naive_or_non_utc_timestamps(timestamp: datetime) -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        SystemState("intersection-1", 0, 0, {}, timestamp)


def test_state_rejects_invalid_counts_and_negative_time() -> None:
    timestamp = datetime(2026, 11, 20, 10, tzinfo=UTC)

    with pytest.raises(ValueError, match="detector counts"):
        SystemState("intersection-1", 0, 0, {"north": -1}, timestamp)
    with pytest.raises(ValueError, match="non-negative"):
        SystemState("intersection-1", 0, -0.1, {}, timestamp)


def test_state_and_action_enforce_schema_string_limits() -> None:
    timestamp = datetime(2026, 11, 20, 10, tzinfo=UTC)

    with pytest.raises(ValueError, match="128 characters"):
        SystemState("i" * 129, 0, 0, {}, timestamp)
    with pytest.raises(ValueError, match="256 characters"):
        Action("intersection-1", 0, "r" * 257, timestamp)


def test_state_rejects_detector_ids_that_collide_after_normalization() -> None:
    timestamp = datetime(2026, 11, 20, 10, tzinfo=UTC)

    with pytest.raises(ValueError, match="remain unique"):
        SystemState(
            "intersection-1",
            0,
            0,
            {"north": 1, " north ": 2},
            timestamp,
        )
