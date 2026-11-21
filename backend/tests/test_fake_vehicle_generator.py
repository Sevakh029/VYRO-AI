import json
from datetime import UTC, datetime
from types import SimpleNamespace

import paho.mqtt.client as mqtt
from vyro_backend.fake_vehicle_generator import (
    PUBLISH_INTERVAL_SECONDS,
    VEHICLE_COUNT,
    VEHICLE_STATE_TOPIC,
    FakeVehicleGenerator,
)
from vyro_backend.schemas import VehicleState


class FakePublishInfo:
    def __init__(self, rc: int = mqtt.MQTT_ERR_SUCCESS) -> None:
        self.rc = rc


class FakeMQTTClient:
    def __init__(self) -> None:
        self.on_connect = None
        self.on_disconnect = None
        self.published: list[tuple[str, str, int]] = []
        self.publish_result = mqtt.MQTT_ERR_SUCCESS

    def reconnect_delay_set(self, min_delay: int, max_delay: int) -> None:
        del min_delay, max_delay

    def publish(self, topic: str, payload: str, qos: int) -> FakePublishInfo:
        self.published.append((topic, payload, qos))
        return FakePublishInfo(self.publish_result)


def connected_generator() -> tuple[FakeVehicleGenerator, FakeMQTTClient]:
    client = FakeMQTTClient()
    generator = FakeVehicleGenerator(client=client)  # type: ignore[arg-type]
    generator._on_connect(
        client, None, None, SimpleNamespace(is_failure=False), None  # type: ignore[arg-type]
    )
    return generator, client


def test_generates_exactly_200_unique_valid_vehicle_states() -> None:
    generator, _ = connected_generator()

    states = generator.generate_states(datetime(2026, 11, 21, tzinfo=UTC))

    assert len(states) == VEHICLE_COUNT == 200
    assert len({state.vehicle_id for state in states}) == VEHICLE_COUNT
    assert all(isinstance(state, VehicleState) for state in states)
    assert states[0].vehicle_id == "fake-vehicle-0001"
    assert states[-1].vehicle_id == "fake-vehicle-0200"
    assert all(state.timestamp.tzinfo == UTC for state in states)


def test_publishes_all_states_on_existing_topic_as_valid_schema_json() -> None:
    generator, client = connected_generator()

    assert generator.publish_once() == 200

    assert len(client.published) == 200
    for topic, payload, qos in client.published:
        assert topic == VEHICLE_STATE_TOPIC
        assert qos == 1
        assert isinstance(VehicleState.model_validate_json(payload), VehicleState)


def test_publish_failure_is_reported_and_does_not_stop_remaining_states(
    caplog,
) -> None:
    generator, client = connected_generator()
    client.publish_result = mqtt.MQTT_ERR_NO_CONN

    assert generator.publish_once() == 0

    assert len(client.published) == VEHICLE_COUNT
    assert "Failed to publish state" in caplog.text


def test_disconnection_skips_publish_until_reconnected() -> None:
    generator, client = connected_generator()
    generator._on_disconnect(
        client,
        None,
        None,
        SimpleNamespace(is_failure=True),
        None,  # type: ignore[arg-type]
    )

    assert generator.publish_once() == 0
    assert client.published == []

    generator._on_connect(
        client, None, None, SimpleNamespace(is_failure=False), None  # type: ignore[arg-type]
    )

    assert generator.publish_once() == VEHICLE_COUNT


def test_run_forever_schedules_each_vehicle_cycle_at_one_second_intervals(
    monkeypatch,
) -> None:
    generator, client = connected_generator()
    now = [0.0]
    monkeypatch.setattr(
        "vyro_backend.fake_vehicle_generator.time.monotonic",
        lambda: now[0],
    )

    class StopAfterTwoWaits:
        waits: list[float] = []

        def is_set(self) -> bool:
            return len(self.waits) == 2

        def wait(self, timeout: float) -> bool:
            self.waits.append(timeout)
            now[0] += timeout
            return False

    stop_event = StopAfterTwoWaits()
    generator.run_forever(stop_event)  # type: ignore[arg-type]

    assert PUBLISH_INTERVAL_SECONDS == 1.0
    assert stop_event.waits == [1.0, 1.0]
    assert len(client.published) == 2 * VEHICLE_COUNT
    assert json.loads(client.published[0][1])["vehicle_id"] == "fake-vehicle-0001"
