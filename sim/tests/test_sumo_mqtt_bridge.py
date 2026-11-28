from datetime import UTC, datetime
from pathlib import Path

import pytest
from vyro_backend.schemas import ControllerAck, IntersectionState, SignalCommand, VehicleState

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


def test_installed_network_projection_converts_sumo_local_position_with_offset() -> None:
    network_file = Path(__file__).parents[1] / "net" / "yerevan_v0.net.xml"
    network = load_network(network_file)
    projection = NetworkProjection(network.convertXY2LonLat)

    latitude, longitude = projection.position_to_latlon(1013.74, 1353.343)

    assert latitude == pytest.approx(40.2075297, abs=1e-6)
    assert longitude == pytest.approx(44.4945618, abs=1e-6)


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


class FakeTrafficLightAPI:
    def __init__(self) -> None:
        self.applied: list[tuple[str, int]] = []
        self.phases = {"signal-1": 0}

    def getIDList(self) -> tuple[str, ...]:
        return ("signal-1",)

    def setPhase(self, signal_id: str, phase: int) -> None:
        self.applied.append((signal_id, phase))
        self.phases[signal_id] = phase

    def getPhase(self, signal_id: str) -> int:
        return self.phases[signal_id]

    def setProgram(self, signal_id: str, program_id: str) -> None:
        del signal_id, program_id

    def getControlledLanes(self, signal_id: str) -> tuple[str, ...]:
        del signal_id
        return ("lane-1",)

    def getSpentTime(self, signal_id: str) -> float:
        del signal_id
        return 12.0


class FakeBridgeTraCI:
    def __init__(self) -> None:
        self.trafficlight = FakeTrafficLightAPI()
        self.vehicle = FakeVehicleAPI()


def test_bridge_applies_valid_command_and_publishes_ack(tmp_path) -> None:
    config = tmp_path / "signals.json"
    config.write_text(
        '{"signals":[{"signal_id":"signal-1","phases":[{"phase":0,"kind":"green","minimum_green_s":20,"yellow_s":0,"all_red_s":0},{"phase":1,"kind":"yellow","minimum_green_s":4,"yellow_s":4,"all_red_s":0},{"phase":2,"kind":"all_red","minimum_green_s":5,"yellow_s":0,"all_red_s":5}],"yellow_phase":1,"all_red_phase":2,"max_wait_s":120}]}',
        encoding="utf-8",
    )
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,
        signals_file=config,
    )
    bridge.connected = True
    traci = FakeBridgeTraCI()
    bridge.attach_traci(traci)
    command = SignalCommand(
        command_id="command-1",
        signal_id="signal-1",
        phase=1,
        hold_s=15,
        reason="yellow",
        ts_utc=datetime.now(UTC),
    )

    ack = bridge.apply_command(command)

    assert traci.trafficlight.applied == [("signal-1", 1)]
    assert ack.applied
    assert ControllerAck.model_validate_json(client.published[-1][1]).command_id == "command-1"


def test_bridge_rejects_unknown_signal_and_phase(tmp_path) -> None:
    config = tmp_path / "signals.json"
    config.write_text('{"signals":[]}', encoding="utf-8")
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        FakeMQTTClient(),
        signals_file=config,
    )
    command = SignalCommand(
        command_id="command-1",
        signal_id="unknown",
        phase=9,
        hold_s=15,
        reason="test",
        ts_utc=datetime.now(UTC),
    )
    ack = bridge.apply_command(command)
    assert not ack.applied
    assert ack.reason == "unknown signal_id"


def test_bridge_publishes_intersection_state(tmp_path) -> None:
    config = tmp_path / "signals.json"
    config.write_text('{"signals":[]}', encoding="utf-8")
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,
        signals_file=config,
    )
    bridge.connected = True

    traci = FakeBridgeTraCI()
    traci.vehicle = type(
        "FakeVehicleLaneAPI",
        (object,),
        {
            "getIDList": lambda self: ("vehicle-1",),
            "getLaneID": lambda self, vehicle_id: "lane-1",
        },
    )()

    assert bridge.publish_intersections(traci, datetime.now(UTC)) == 1
    topic, payload, qos = client.published[-1]
    assert topic == "vyro/v1/intersection/state"
    assert qos == 1
    state = IntersectionState.model_validate_json(payload)
    assert state.intersection_id == "signal-1"
