from datetime import UTC, datetime

from vyro_backend.schemas import VehicleState
from vyro_backend.vehicle_agent import VehicleAgentRunner, haversine_m


def state(vehicle_id: str, latitude: float, longitude: float) -> VehicleState:
    return VehicleState(
        vehicle_id=vehicle_id,
        latitude=latitude,
        longitude=longitude,
        speed_mps=10,
        timestamp=datetime(2026, 11, 23, tzinfo=UTC),
    )


def test_agent_runner_uses_fixed_penetration_and_neighbour_radius() -> None:
    runner = VehicleAgentRunner(penetration=1.0, radius_m=300.0, seed=100)

    neighbours = runner.receive(state("vehicle-1", 40.1800, 44.5100))
    assert neighbours == []

    neighbours = runner.receive(state("vehicle-2", 40.1801, 44.5100))
    assert set(neighbours or []) == {"vehicle-1"}


def test_agent_runner_can_disable_connected_vehicle_reports() -> None:
    runner = VehicleAgentRunner(penetration=0.0)

    assert runner.receive(state("vehicle-1", 40.1800, 44.5100)) is None
    assert runner.agents == {}


def test_haversine_returns_expected_small_distance() -> None:
    first = state("one", 40.1800, 44.5100)
    second = state("two", 40.1810, 44.5100)

    assert 100 < haversine_m(first, second) < 120
