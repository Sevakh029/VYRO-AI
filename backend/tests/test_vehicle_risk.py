from datetime import UTC, datetime

from vyro_backend.schemas import VehicleState
from vyro_backend.vehicle_risk import (
    predict_position,
    risk_advisories,
    time_to_collision,
)


def vehicle(vehicle_id: str, latitude: float, speed_mps: float) -> VehicleState:
    return VehicleState(
        vehicle_id=vehicle_id,
        latitude=latitude,
        longitude=44.51,
        speed_mps=speed_mps,
        heading_deg=0,
        timestamp=datetime(2026, 11, 23, tzinfo=UTC),
        schema_version="v1.1",
    )


def test_predict_position_is_bounded_to_supported_horizon() -> None:
    state = vehicle("vehicle-1", 40.18, 10)

    latitude, longitude = predict_position(state, 5)

    assert latitude > state.latitude
    assert longitude == state.longitude
    try:
        predict_position(state, 11)
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported horizon was accepted")


def test_ttc_flags_closing_vehicles_and_handles_safe_edge_cases() -> None:
    follower = vehicle("follower", 40.1800, 20)
    leader = vehicle("leader", 40.1810, 10)

    ttc = time_to_collision(follower, leader)

    assert ttc is not None
    assert ttc > 0
    assert time_to_collision(leader, follower) is None
    assert time_to_collision(follower, vehicle("slow", 40.1801, 20)) is None


def test_risk_advisory_is_emitted_for_a_fast_closing_vehicle() -> None:
    follower = vehicle("follower", 40.1800, 30)
    leader = vehicle("leader", 40.1801, 5)

    advisories = risk_advisories([follower, leader], risk_threshold_s=3)

    assert len(advisories) == 1
    assert advisories[0].vehicle_id == "follower"
    assert advisories[0].advisory_type == "risk"
