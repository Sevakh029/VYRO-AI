from datetime import UTC, datetime
from pathlib import Path

import pytest
from vyro_backend.schemas import VehicleState

from sim.sumo_mqtt_bridge import NetworkProjection, SumoMqttBridge, load_network


class FakePublishResult:
    def __init__(self, rc: int = 0) -> None:
        self.rc = rc


class FakeMQTTClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, int]] = []
        self.publish_rc = 0

    def publish(self, topic: str, payload: str, qos: int) -> FakePublishResult:
        self.published.append((topic, payload, qos))
        return FakePublishResult(self.publish_rc)


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


class FakeReasonCode:
    def __init__(self, is_failure: bool) -> None:
        self.is_failure = is_failure


def test_network_position_is_converted_to_geographic_coordinates() -> None:
    projection = NetworkProjection(
        lambda x, y: (44 + x / 1000, 40 + y / 1000),
    )

    assert projection.position_to_latlon(492, 206) == pytest.approx((40.206, 44.492))


def test_installed_network_projection_maps_candidate_to_yerevan() -> None:
    network_file = (
        Path(__file__).parents[1]
        / "net"
        / "yerevan_v0.net.xml"
    )
    network = load_network(network_file)
    x, y = network.getEdges()[0].getShape()[0]

    longitude, latitude = network.convertXY2LonLat(x, y)

    assert 44.48 <= longitude <= 44.51
    assert 40.19 <= latitude <= 40.22


def test_bridge_publishes_valid_vehicle_state_when_connected() -> None:
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,  # type: ignore[arg-type]
    )
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


def test_bridge_skips_publish_when_disconnected() -> None:
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,  # type: ignore[arg-type]
    )

    assert bridge.publish_positions(FakeTraCI()) == 0
    assert client.published == []


def test_paho_v2_connect_callback_sets_connection_state() -> None:
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        FakeMQTTClient(),  # type: ignore[arg-type]
    )

    bridge.on_connect(None, None, None, FakeReasonCode(False), None)  # type: ignore[arg-type]

    assert bridge.connected is True
    bridge.wait_until_connected(timeout=0)


def test_paho_v2_failed_connect_callback_keeps_bridge_disconnected() -> None:
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        FakeMQTTClient(),  # type: ignore[arg-type]
    )

    bridge.on_connect(None, None, None, FakeReasonCode(True), None)  # type: ignore[arg-type]

    assert bridge.connected is False
    with pytest.raises(ConnectionError, match="broker rejected"):
        bridge.wait_until_connected(timeout=0)


def test_bridge_times_out_when_mqtt_never_connects() -> None:
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        FakeMQTTClient(),  # type: ignore[arg-type]
    )

    with pytest.raises(TimeoutError, match="Timed out"):
        bridge.wait_until_connected(timeout=0)


def test_paho_disconnect_callback_clears_connected_state() -> None:
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        FakeMQTTClient(),  # type: ignore[arg-type]
    )
    bridge.on_connect(None, None, None, FakeReasonCode(False), None)  # type: ignore[arg-type]

    bridge.on_disconnect(None, None, None, None, None)  # type: ignore[arg-type]

    assert bridge.connected is False


def test_bridge_counts_only_successful_mqtt_publish_results() -> None:
    client = FakeMQTTClient()
    client.publish_rc = 4
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,  # type: ignore[arg-type]
    )
    bridge.connected = True

    assert bridge.publish_positions(FakeTraCI()) == 0
    assert len(client.published) == 1
