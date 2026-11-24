import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect
from vyro_backend.message_handler import MESSAGE_SCHEMAS, MQTTMessageHandler
from vyro_backend.mqtt_subscriber import MQTTSubscriber
from vyro_backend.schemas import (
    ControllerAck,
    IntersectionState,
    MetricsSnapshot,
    PreemptionRequest,
    SignalCommand,
    VehicleAdvisory,
    VehicleState,
)
from vyro_backend.websocket_manager import WebSocketManager

UTC_TIMESTAMP = "2026-11-21T10:00:00Z"

VALID_MESSAGES = [
    (
        "vyro/v1/vehicle/state",
        {
            "vehicle_id": "vehicle-1",
            "latitude": 40.18,
            "longitude": 44.51,
            "speed_mps": 12.5,
            "timestamp": UTC_TIMESTAMP,
        },
        VehicleState,
        "vehicle-1",
    ),
    (
        "vyro/v1/intersection/state",
        {
            "intersection_id": "intersection-1",
            "phase_id": 2,
            "time_in_phase_s": 15.5,
            "timestamp": UTC_TIMESTAMP,
        },
        IntersectionState,
        "intersection-1",
    ),
    (
        "vyro/v1/controller/command",
        {
            "intersection_id": "intersection-1",
            "phase_id": 1,
            "reason": "queue_pressure",
            "timestamp": UTC_TIMESTAMP,
        },
        SignalCommand,
        "intersection-1",
    ),
    (
        "vyro/v1/controller/ack",
        {
            "command_id": "command-1",
            "intersection_id": "intersection-1",
            "applied": True,
            "reason": "applied",
            "timestamp": UTC_TIMESTAMP,
        },
        ControllerAck,
        "intersection-1",
    ),
    (
        "vyro/v1/vehicle/advisory",
        {
            "vehicle_id": "vehicle-1",
            "advisory_type": "speed",
            "message": "slow down",
            "timestamp": UTC_TIMESTAMP,
        },
        VehicleAdvisory,
        "vehicle-1",
    ),
    (
        "vyro/v1/metrics/snapshot",
        {
            "vehicle_count": 2,
            "mean_speed_mps": 5,
            "stopped_vehicle_count": 0,
            "timestamp": UTC_TIMESTAMP,
        },
        MetricsSnapshot,
        True,
    ),
    (
        "vyro/v1/preemption/request",
        {
            "intersection_id": "intersection-1",
            "vehicle_id": "ambulance-1",
            "lead_time_s": 8,
            "timestamp": UTC_TIMESTAMP,
        },
        PreemptionRequest,
        "ambulance-1",
    ),
]


@pytest.mark.parametrize(("topic", "message", "schema", "entity_id"), VALID_MESSAGES)
def test_supported_mqtt_message_types_validate(topic, message, schema, entity_id) -> None:
    handler = MQTTMessageHandler(WebSocketManager())

    assert handler(topic, json.dumps(message).encode()) == entity_id
    assert isinstance(schema.model_validate(message), schema)


@pytest.mark.parametrize(
    ("topic", "payload"),
    [
        ("vyro/v1/vehicle/state", b"{malformed"),
        ("vyro/v1/vehicle/state", b'{"vehicle_id":"vehicle-1"}'),
        ("vyro/v1/controller/ack", b'{"anything":"unused"}'),
    ],
)
def test_invalid_or_unsupported_messages_are_not_stored(topic: str, payload: bytes) -> None:
    subscriber = MQTTSubscriber(on_message=MQTTMessageHandler(WebSocketManager()))
    message = type(
        "MQTTMessage",
        (),
        {"topic": topic, "payload": payload, "_topic": topic.encode()},
    )()

    subscriber._on_mqtt_message(subscriber.client, None, message)  # type: ignore[arg-type]

    assert subscriber.get_latest(topic) is None


def test_disconnected_websocket_client_is_removed_without_blocking_others() -> None:
    manager = WebSocketManager()
    disconnected = AsyncMock()
    disconnected.send_json.side_effect = WebSocketDisconnect()
    connected = AsyncMock()
    manager._connections.update({disconnected, connected})

    asyncio.run(manager.broadcast({"vehicle_id": "vehicle-1"}))

    disconnected.send_json.assert_awaited_once()
    connected.send_json.assert_awaited_once_with({"vehicle_id": "vehicle-1"})
    assert disconnected not in manager._connections
    assert connected in manager._connections


def test_schema_registry_uses_existing_schema_types() -> None:
    assert MESSAGE_SCHEMAS["vyro/v1/vehicle/state"] is VehicleState
    assert MESSAGE_SCHEMAS["vyro/v1/intersection/state"] is IntersectionState
    assert MESSAGE_SCHEMAS["vyro/v1/controller/command"] is SignalCommand
    assert MESSAGE_SCHEMAS["vyro/v1/controller/ack"] is ControllerAck
    assert MESSAGE_SCHEMAS["vyro/v1/vehicle/advisory"] is VehicleAdvisory
    assert MESSAGE_SCHEMAS["vyro/v1/metrics/snapshot"] is MetricsSnapshot
    assert MESSAGE_SCHEMAS["vyro/v1/preemption/request"] is PreemptionRequest
