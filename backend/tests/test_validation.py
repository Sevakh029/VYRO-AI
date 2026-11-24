from datetime import UTC, datetime

from vyro_backend.schemas import VehicleState
from vyro_backend.validation import RateLimiter, validate_vehicle_state


def test_vehicle_validation_rejects_impossible_coordinates_and_speeds() -> None:
    timestamp = datetime(2026, 11, 23, tzinfo=UTC)
    off_network = VehicleState.model_construct(
        vehicle_id="vehicle-off-network",
        latitude=91,
        longitude=44.51,
        speed_mps=10,
        timestamp=timestamp,
    )
    impossible_speed = VehicleState.model_construct(
        vehicle_id="vehicle-fast",
        latitude=40.18,
        longitude=44.51,
        speed_mps=float("nan"),
        heading_deg=0,
        timestamp=timestamp,
    )

    assert not validate_vehicle_state(off_network)
    assert not validate_vehicle_state(impossible_speed)


def test_rate_limiter_rejects_load_above_limit() -> None:
    limiter = RateLimiter(max_messages_per_second=2)

    assert limiter.allow()
    assert limiter.allow()
    assert not limiter.allow()
