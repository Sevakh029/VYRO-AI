from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from vyro_backend.schemas import (
    ControllerAck,
    IntersectionState,
    SignalCommand,
    VehicleState,
)

from sim.sumo_mqtt_bridge import (
    ACK_TOPIC,
    COMMAND_TOPIC,
    INTERSECTION_STATE_TOPIC,
    NetworkProjection,
    SumoMqttBridge,
    load_network,
)


class FakePublishResult:
    def __init__(self, rc: int = 0) -> None:
        self.rc = rc


class FakeMQTTClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, int]] = []
        self.subscriptions: list[tuple[str, int]] = []
        self.publish_rc = 0

    def subscribe(self, topic: str, qos: int) -> None:
        self.subscriptions.append((topic, qos))

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


class FakeLaneAPI:
    counts = {
        "approach_north_0": 2,
        "approach_north_1": 3,
        "approach_south_0": 4,
    }

    def getLastStepVehicleNumber(self, lane_id: str) -> int:
        return self.counts[lane_id]


class FakeTrafficLightAPI:
    def __init__(self) -> None:
        self.phase = 0
        self.calls: list[tuple[str, int]] = []

    def getPhase(self, signal_id: str) -> int:
        del signal_id
        return self.phase

    def setPhase(self, signal_id: str, phase_id: int) -> None:
        self.calls.append((signal_id, phase_id))
        self.phase = phase_id


class FakePhaseTraCI:
    def __init__(self) -> None:
        self.trafficlight = FakeTrafficLightAPI()


class FakeIntersectionTraCI:
    lane = FakeLaneAPI()

    class TrafficLightAPI:
        def getPhase(self, signal_id: str) -> int:
            del signal_id
            return 2

        def getSpentDuration(self, signal_id: str) -> float:
            del signal_id
            return 15.5

    trafficlight = TrafficLightAPI()


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
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,  # type: ignore[arg-type]
    )

    bridge.on_connect(client, None, None, FakeReasonCode(False), None)  # type: ignore[arg-type]

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


def test_bridge_publishes_intersection_state_with_per_approach_detector_counts(
    tmp_path: Path,
) -> None:
    signals_file = tmp_path / "signals.json"
    signals_file.write_text(
        '[{"signal_id":"signal-1","valid_phase_indices":[0,1,2],'
        '"approaches":["approach_north","approach_south"],'
        '"lanes":["approach_north_0","approach_north_1","approach_south_0"]}]',
        encoding="utf-8",
    )
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,  # type: ignore[arg-type]
        signals_file=signals_file,
    )
    bridge.connected = True
    timestamp = datetime(2026, 11, 24, 12, tzinfo=UTC)

    assert bridge.publish_intersection_states(FakeIntersectionTraCI(), timestamp) == 1

    topic, payload, qos = client.published[0]
    state = IntersectionState.model_validate_json(payload)
    assert topic == INTERSECTION_STATE_TOPIC
    assert qos == 1
    assert state.intersection_id == "signal-1"
    assert state.phase_id == 2
    assert state.time_in_phase_s == 15.5
    assert state.detector_counts == {"approach_north": 5, "approach_south": 4}
    assert state.timestamp == timestamp


def test_bridge_skips_intersection_publish_when_disconnected(tmp_path: Path) -> None:
    signals_file = tmp_path / "signals.json"
    signals_file.write_text(
        '[{"signal_id":"signal-1","valid_phase_indices":[0],'
        '"lanes":["approach_north_0"]}]',
        encoding="utf-8",
    )
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,  # type: ignore[arg-type]
        signals_file=signals_file,
    )

    assert bridge.publish_intersection_states(FakeIntersectionTraCI()) == 0
    assert client.published == []


def test_bridge_rejects_invalid_phase_without_changing_traci(tmp_path: Path) -> None:
    signals_file = tmp_path / "signals.json"
    signals_file.write_text(
        '[{"signal_id":"signal-1","valid_phase_indices":[0,1]}]',
        encoding="utf-8",
    )
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,  # type: ignore[arg-type]
        signals_file=signals_file,
    )
    bridge.connected = True
    traci = FakePhaseTraCI()
    traci.trafficlight.phase = 1
    command = SignalCommand(
        intersection_id="signal-1",
        phase_id=99,
        reason="pressure",
        timestamp=datetime(2026, 11, 24, 12, tzinfo=UTC),
        command_id="command-1",
    )

    result = bridge.apply_phase_command(traci, command)

    assert traci.trafficlight.calls == []
    assert traci.trafficlight.getPhase("signal-1") == 1
    assert result["applied"] is False
    assert "invalid phase index 99" in result["reason"]
    topic, payload, qos = client.published[-1]
    ack = ControllerAck.model_validate_json(payload)
    assert topic == ACK_TOPIC
    assert qos == 1
    assert ack.applied is False
    assert ack.command_id == "command-1"


def test_bridge_applies_valid_phase(tmp_path: Path) -> None:
    signals_file = tmp_path / "signals.json"
    signals_file.write_text(
        '[{"signal_id":"signal-1","valid_phase_indices":[0,1]}]',
        encoding="utf-8",
    )
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        FakeMQTTClient(),  # type: ignore[arg-type]
        signals_file=signals_file,
    )
    traci = FakePhaseTraCI()
    command = {
        "intersection_id": "signal-1",
        "phase_id": 1,
        "reason": "pressure",
        "timestamp": "2026-11-24T12:00:00Z",
    }

    result = bridge.apply_phase_command(traci, command)

    assert result["applied"] is True
    assert traci.trafficlight.calls == [("signal-1", 1)]


@pytest.mark.parametrize(
    ("phase_id", "expected_applied", "expected_phase", "expected_reason"),
    [
        (1, True, 1, "phase applied"),
        (99, False, 0, "invalid phase index 99"),
    ],
)
def test_bridge_processes_mqtt_phase_commands_and_publishes_ack(
    tmp_path: Path,
    phase_id: int,
    expected_applied: bool,
    expected_phase: int,
    expected_reason: str,
) -> None:
    signals_file = tmp_path / "signals.json"
    signals_file.write_text(
        '[{"signal_id":"signal-1","valid_phase_indices":[0,1]}]',
        encoding="utf-8",
    )
    client = FakeMQTTClient()
    bridge = SumoMqttBridge(
        NetworkProjection(lambda x, y: (44.492, 40.206)),
        client,  # type: ignore[arg-type]
        signals_file=signals_file,
    )
    traci = FakePhaseTraCI()
    bridge.set_traci(traci)
    bridge.on_connect(client, None, None, FakeReasonCode(False), None)  # type: ignore[arg-type]
    command = SignalCommand(
        intersection_id="signal-1",
        phase_id=phase_id,
        reason="queue_pressure",
        timestamp=datetime(2026, 11, 24, 12, tzinfo=UTC),
        command_id="command-1",
    )
    bridge.on_message(
        client,
        None,
        SimpleNamespace(topic=COMMAND_TOPIC, payload=command.model_dump_json().encode()),
    )

    assert bridge.process_pending_commands() == 1

    assert client.subscriptions == [(COMMAND_TOPIC, 1)]
    assert traci.trafficlight.calls == (
        [("signal-1", phase_id)] if expected_applied else []
    )
    assert traci.trafficlight.getPhase("signal-1") == expected_phase
    topic, payload, qos = client.published[-1]
    ack = ControllerAck.model_validate_json(payload)
    assert topic == ACK_TOPIC
    assert qos == 1
    assert ack.command_id == "command-1"
    assert ack.applied is expected_applied
    assert expected_reason in ack.reason
