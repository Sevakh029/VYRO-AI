import json
import sqlite3

import paho.mqtt.client as mqtt
import pytest
from fastapi.testclient import TestClient
from vyro_backend.app import app, mqtt_message_handler, mqtt_subscriber

VEHICLE_TOPIC = "vyro/v1/vehicle/state"


def make_message(topic: str, payload: bytes) -> mqtt.MQTTMessage:
    message = mqtt.MQTTMessage(topic=topic.encode("utf-8"))
    message._topic = topic.encode("utf-8")
    message.payload = payload
    return message


def test_valid_message_reaches_multiple_websocket_clients(tmp_path, monkeypatch) -> None:
    database = tmp_path / "websocket.db"
    logger = mqtt_message_handler.sqlite_logger
    assert logger is not None
    monkeypatch.setattr(logger, "database_path", database)
    monkeypatch.setattr(logger, "_initialized", False)
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
            logger.flush(timeout=5)

            expected_broadcast = {
                **message,
                "schema_version": "0.2",
                "vehicle_type": "unknown",
                "topic": VEHICLE_TOPIC,
            }
            assert first.receive_json() == expected_broadcast
            assert second.receive_json() == expected_broadcast
            latest = mqtt_subscriber.get_latest(VEHICLE_TOPIC)
            assert latest is not None
            assert json.loads(latest) == message
            assert "ws-vehicle-1" in mqtt_subscriber.store.get_entities(VEHICLE_TOPIC)
            with sqlite3.connect(database) as connection:
                payload = connection.execute(
                    "SELECT payload FROM received_messages"
                ).fetchone()
            assert json.loads(payload[0]) == message


def test_invalid_message_is_not_broadcast_or_stored(tmp_path, monkeypatch) -> None:
    database = tmp_path / "invalid-websocket.db"
    logger = mqtt_message_handler.sqlite_logger
    assert logger is not None
    monkeypatch.setattr(logger, "database_path", database)
    monkeypatch.setattr(logger, "_initialized", False)
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
            logger.flush(timeout=5)

            assert websocket.receive_json() == {
                **valid,
                "schema_version": "0.2",
                "vehicle_type": "unknown",
                "topic": VEHICLE_TOPIC,
            }

    assert mqtt_subscriber.get_latest(VEHICLE_TOPIC) == json.dumps(valid).encode()
    assert "ws-vehicle-invalid" not in mqtt_subscriber.store.get_entities(VEHICLE_TOPIC)


@pytest.mark.parametrize(
    ("topic", "message"),
    [
        (
            "vyro/v1/controller/ack",
            {
                "command_id": "command-1",
                "intersection_id": "intersection-1",
                "applied": True,
                "reason": "applied",
                "timestamp": "2026-11-21T10:00:00Z",
            },
        ),
        (
            "vyro/v1/metrics/snapshot",
            {
                "vehicle_count": 4,
                "mean_speed_mps": 6.5,
                "stopped_vehicle_count": 1,
                "timestamp": "2026-11-21T10:00:00Z",
            },
        ),
    ],
)
def test_ack_and_metrics_topics_are_broadcast_with_topic(
    topic: str, message: dict, tmp_path, monkeypatch
) -> None:
    logger = mqtt_message_handler.sqlite_logger
    assert logger is not None
    monkeypatch.setattr(logger, "database_path", tmp_path / "topic.db")
    monkeypatch.setattr(logger, "_initialized", False)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            mqtt_subscriber._on_mqtt_message(
                mqtt_subscriber.client,
                None,
                make_message(topic, json.dumps(message).encode()),
            )
            logger.flush(timeout=5)

            assert websocket.receive_json() == {
                **message,
                "schema_version": "0.2",
                "topic": topic,
            }
