import json

from fastapi.testclient import TestClient
from vyro_backend.app import app, mqtt_subscriber

VEHICLE_TOPIC = "vyro/v1/vehicle/state"


def make_message(topic: str, payload: bytes):
    return type(
        "MQTTMessage",
        (),
        {"topic": topic, "payload": payload, "_topic": topic.encode("utf-8")},
    )()


def test_valid_message_reaches_multiple_websocket_clients() -> None:
    message = {
        "vehicle_id": "ws-vehicle-1",
        "latitude": 40.18,
        "longitude": 44.51,
        "speed_mps": 12.5,
        "heading_deg": 0.0,
        "timestamp": "2026-11-21T10:00:00Z",
    }

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as first, client.websocket_connect("/ws") as second:
            mqtt_subscriber._on_mqtt_message(
                mqtt_subscriber.client,
                None,
                make_message(VEHICLE_TOPIC, json.dumps(message).encode()),
            )

            assert first.receive_json() == message
            assert second.receive_json() == message
            assert json.loads(mqtt_subscriber.get_latest(VEHICLE_TOPIC)) == message
            assert "ws-vehicle-1" in mqtt_subscriber.store.get_entities(VEHICLE_TOPIC)


def test_invalid_message_is_not_broadcast_or_stored() -> None:
    invalid = {
        "vehicle_id": "ws-vehicle-invalid",
        "latitude": 91,
        "longitude": 44.51,
        "speed_mps": 12.5,
        "heading_deg": 0.0,
        "timestamp": "2026-11-21T10:00:00Z",
    }
    valid = {
        "vehicle_id": "ws-vehicle-valid",
        "latitude": 40.18,
        "longitude": 44.51,
        "speed_mps": 12.5,
        "heading_deg": 0.0,
        "timestamp": "2026-11-21T10:00:00Z",
    }
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            mqtt_subscriber._on_mqtt_message(
                mqtt_subscriber.client,
                None,
                make_message(VEHICLE_TOPIC, json.dumps(invalid).encode()),
            )
            mqtt_subscriber._on_mqtt_message(
                mqtt_subscriber.client,
                None,
                make_message(VEHICLE_TOPIC, json.dumps(valid).encode()),
            )

            assert websocket.receive_json() == valid

    assert mqtt_subscriber.get_latest(VEHICLE_TOPIC) == json.dumps(valid).encode()
    assert "ws-vehicle-invalid" not in mqtt_subscriber.store.get_entities(VEHICLE_TOPIC)
