from datetime import UTC, datetime

import pytest
from vyro_controller.estimator import ProbeVehicle, estimate_queues, estimate_state
from vyro_controller.state import SystemState

TIMESTAMP = datetime(2026, 11, 20, 10, tzinfo=UTC)


def test_estimator_fuses_per_approach_counts_with_queued_near_stop_line_probes() -> None:
    state = SystemState(
        "intersection-1",
        0,
        12,
        {"north": 3, "east": 1, "south": 1},
        TIMESTAMP,
    )
    probes = [
        ProbeVehicle("north", 10, 0.2),
        ProbeVehicle("north", 20, 0.1),
        ProbeVehicle("east", 8, 0.0),
        ProbeVehicle("east", 8, 2.0),
        ProbeVehicle("south", 10, 0.1),
        ProbeVehicle("south", 20, 0.2),
        ProbeVehicle("south", 51, 0.0),
    ]

    estimates = estimate_queues(state, probes)

    assert estimates == {"north": 3, "east": 1, "south": 2}
    assert estimate_state(state, probes).detector_counts == estimates


def test_estimator_includes_probe_only_approaches_and_validates_thresholds() -> None:
    state = SystemState("intersection-1", 0, 0, {}, TIMESTAMP)

    assert estimate_queues(
        state,
        [ProbeVehicle("south", 50, 0.5)],
    ) == {"south": 1}
    with pytest.raises(ValueError, match="near_stop_line_m"):
        estimate_queues(state, near_stop_line_m=float("inf"))
    with pytest.raises(ValueError, match="speed_mps"):
        ProbeVehicle("north", 1, float("nan"))
