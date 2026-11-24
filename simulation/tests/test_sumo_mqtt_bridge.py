from datetime import UTC, datetime

import pytest
from vyro_backend.schemas import VehicleState

from simulation.sumo_mqtt_bridge import NetworkBounds, SumoMqttBridge


class FakePublishResult:
    rc = 0


class FakeMQTTClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, int]] = []

    def publish(self, topic: str, payload: str, qos: int) -> FakePublishResult:
        self.published.append((topic, payload, qos))
        return FakePublishResult()


class FakeVehicleAPI:
    def getIDList(self) -> tuple[str, ...]:
        return ("real-vehicle-1",)

    def getPosition(self, vehicle_id: str) -> tuple[float, float]:
        del vehicle_id
        return (500.0, 250.0)

    def getSpeed(self, vehicle_id: str) -> float:
        del vehicle_id
        return 12.5

    def getAngle(self, vehicle_id: str) -> float:
        del vehicle_id
        return 90.0


class FakeTraCI:
    vehicle = FakeVehicleAPI()


def test_network_position_is_converted_to_geographic_coordinates() -> None:
    bounds = NetworkBounds(
        west=44.488,
        south=40.202,
        east=44.496,
        north=40.210,
        sumo_west=0,
        sumo_south=0,
        sumo_east=1000,
        sumo_north=500,
    )

    latitude, longitude = bounds.position_to_latlon(500, 250)

    assert latitude == pytest.approx(40.206)
    assert longitude == pytest.approx(44.492)


def test_bridge_publishes_valid_vehicle_state_when_connected() -> None:
    bounds = NetworkBounds(44.488, 40.202, 44.496, 40.210, 0, 0, 1000, 500)
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(bounds, client)  # type: ignore[arg-type]
    bridge.connected = True

    published = bridge.publish_positions(
        FakeTraCI(),
        timestamp=datetime(2026, 11, 24, 12, tzinfo=UTC),
    )

    assert published == 1
    topic, payload, qos = client.published[0]
    state = VehicleState.model_validate_json(payload)
    assert topic == "vyro/v1/vehicle/state"
    assert qos == 1
    assert state.vehicle_id == "real-vehicle-1"
    assert state.speed_mps == 12.5
    assert state.heading_deg == 90
