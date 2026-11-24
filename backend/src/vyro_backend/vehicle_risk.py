import math
from collections.abc import Iterable

from .schemas import VehicleAdvisory, VehicleState


def predict_position(
    state: VehicleState,
    horizon_s: float = 5.0,
    route_heading_deg: float | None = None,
) -> tuple[float, float]:
    if not 5.0 <= horizon_s <= 10.0:
        raise ValueError("prediction horizon must be between 5 and 10 seconds")
    heading = state.heading_deg if route_heading_deg is None else route_heading_deg
    heading_radians = math.radians(heading)
    distance_m = state.speed_mps * horizon_s
    latitude_delta = distance_m * math.cos(heading_radians) / 111_320.0
    longitude_delta = distance_m * math.sin(heading_radians) / (
        111_320.0 * max(0.1, math.cos(math.radians(state.latitude)))
    )
    return state.latitude + latitude_delta, state.longitude + longitude_delta


def time_to_collision(
    follower: VehicleState,
    leader: VehicleState,
) -> float | None:
    distance_m = haversine_m(follower, leader)
    if distance_m <= 0.0:
        return 0.0
    relative_speed = follower.speed_mps - leader.speed_mps
    if relative_speed <= 0.0:
        return None
    return distance_m / relative_speed


def risk_advisories(
    states: Iterable[VehicleState],
    risk_threshold_s: float = 3.0,
) -> list[VehicleAdvisory]:
    advisories: list[VehicleAdvisory] = []
    ordered = list(states)
    for follower in ordered:
        for leader in ordered:
            if follower.vehicle_id == leader.vehicle_id:
                continue
            distance_m = haversine_m(follower, leader)
            if distance_m > 200.0:
                continue
            ttc = time_to_collision(follower, leader)
            if ttc is not None and ttc <= risk_threshold_s:
                advisories.append(
                    VehicleAdvisory(
                        vehicle_id=follower.vehicle_id,
                        advisory_type="risk",
                        message=f"Collision risk with {leader.vehicle_id}",
                        timestamp=follower.timestamp,
                        schema_version="0.2",
                    )
                )
                break
    return advisories


def haversine_m(first: VehicleState, second: VehicleState) -> float:
    first_lat = math.radians(first.latitude)
    second_lat = math.radians(second.latitude)
    latitude_delta = second_lat - first_lat
    longitude_delta = math.radians(second.longitude - first.longitude)
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(first_lat) * math.cos(second_lat) * math.sin(longitude_delta / 2) ** 2
    )
    return 6371000.0 * 2 * math.asin(min(1.0, math.sqrt(value)))
