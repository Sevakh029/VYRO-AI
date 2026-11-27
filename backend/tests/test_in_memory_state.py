from datetime import UTC, datetime

from vyro_backend.in_memory_state import InMemoryTrafficState
from vyro_backend.schemas import IntersectionState, SignalCommand, VehicleState


def test_in_memory_state_keeps_latest_entities_and_scenario() -> None:
    state = InMemoryTrafficState()
    timestamp = datetime(2026, 11, 23, tzinfo=UTC)

    state.receive_vehicle(
        VehicleState(
            vehicle_id="vehicle-1",
            latitude=40.18,
            longitude=44.51,
            speed_mps=10,
            timestamp=timestamp,
        )
    )
    state.receive_intersection(
        IntersectionState(
            intersection_id="intersection-1",
            phase_id=2,
            time_in_phase_s=12,
            timestamp=timestamp,
        )
    )
    state.receive_command(
        SignalCommand(
            command_id="command-1",
            signal_id="signal-1",
            phase=1,
            hold_s=15.0,
            reason="queue_pressure",
            ts_utc=timestamp,
        )
    )
    state.set_scenario("normal", "running")

    snapshot = state.snapshot()

    assert "vehicle-1" in snapshot["vehicles"]
    assert "intersection-1" in snapshot["intersections"]
    assert "signal-1" in snapshot["commands"]
    assert snapshot["scenario"] == {"name": "normal", "status": "running"}
