import time
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from vyro_backend.command_bus import (
    ACK_TOPIC,
    COMMAND_TOPIC,
    AcknowledgementHandler,
    CommandBus,
    MQTTCommandPublisher,
)
from vyro_backend.schemas import ControllerAck, SignalCommand


def test_command_bus_publishes_batch_with_v11_ids_and_ack_cancels_fallback() -> None:
    published = []
    bus = CommandBus(published.append, timeout_s=0.1)

    commands = bus.publish_batch(
        [
            {"signal_id": "signal-1", "phase": 2, "hold_s": 15.0, "reason": "pressure"},
            {"signal_id": "signal-2", "phase": 1, "hold_s": 15.0, "reason": "pressure"},
        ]
    )

    assert [command.signal_id for command in commands] == [
        "signal-1",
        "signal-2",
    ]
    assert all(command.command_id for command in commands)
    ack = ControllerAck(
        command_id=commands[0].command_id,
        signal_id="signal-1",
        phase=2,
        hold_s=15.0,
        applied=True,
        reason="applied",
        ts_utc=datetime.now(UTC),
    )
    assert bus.acknowledge(ack)
    time.sleep(0.15)
    assert bus.fallback_count == 1
    bus.close()


def test_command_bus_fallback_is_counted_when_ack_never_arrives() -> None:
    bus = CommandBus(lambda command: None, timeout_s=0.01)

    bus.publish("signal-1", 2, 15.0, "pressure")
    time.sleep(0.03)

    assert bus.fallback_count == 1
    bus.close()


def test_successful_and_rejected_acknowledgements_are_recorded() -> None:
    published = []
    bus = CommandBus(published.append, timeout_s=0.1)
    applied = bus.publish("signal-1", 2, 15.0, "pressure")
    accepted = ControllerAck(
        command_id=applied.command_id,
        signal_id="signal-1",
        phase=2,
        hold_s=15.0,
        applied=True,
        reason="phase applied",
        ts_utc=datetime.now(UTC),
    )
    assert bus.acknowledge(accepted)
    assert bus.statuses[applied.command_id]["status"] == "applied"

    rejected_command = bus.publish("signal-2", 1, 10.0, "pressure")
    rejected = ControllerAck(
        command_id=rejected_command.command_id,
        signal_id="signal-2",
        phase=1,
        hold_s=10.0,
        applied=False,
        reason="invalid phase",
        ts_utc=datetime.now(UTC),
    )
    assert not bus.acknowledge(rejected)
    assert bus.statuses[rejected_command.command_id]["status"] == "rejected"
    bus.close()


def test_unknown_acknowledgement_is_not_applied() -> None:
    bus = CommandBus(lambda command: None)
    ack = ControllerAck(
        command_id="unknown-command",
        signal_id="signal-1",
        phase=1,
        hold_s=15.0,
        applied=True,
        reason="applied",
        ts_utc=datetime.now(UTC),
    )

    assert bus.acknowledge(ack) is False
    assert bus.statuses["unknown-command"]["status"] == "unknown"
    bus.close()


def test_acknowledgement_handler_rejects_malformed_and_unknown_payloads() -> None:
    bus = CommandBus(lambda command: None)
    handler = AcknowledgementHandler(bus)

    assert handler.receive(ACK_TOPIC, b"{malformed") is False
    assert handler.receive(ACK_TOPIC, b'{"anything":"unused"}') is False
    assert handler.receive("vyro/v1/other", b"ignored") is True
    bus.close()


def test_mqtt_command_publisher_uses_agreed_topic_and_qos() -> None:
    class FakeBridge:
        def __init__(self) -> None:
            self.calls = []

        def publish(self, topic: str, payload: str, qos: int) -> object:
            self.calls.append((topic, payload, qos))
            return None

    bridge = FakeBridge()
    publisher = MQTTCommandPublisher(bridge)
    command = SignalCommand(
        command_id="command-1",
        signal_id="signal-1",
        phase=1,
        hold_s=15.0,
        reason="pressure",
        ts_utc=datetime.now(UTC),
    )

    publisher(command)

    assert bridge.calls[0][0] == COMMAND_TOPIC
    assert bridge.calls[0][2] == 1
    assert '"signal_id":"signal-1"' in bridge.calls[0][1]


def test_publication_failure_is_recorded_and_raised() -> None:
    def failing_publisher(command: SignalCommand) -> object:
        del command
        raise OSError("broker unavailable")

    bus = CommandBus(failing_publisher)
    with pytest.raises(OSError, match="broker unavailable"):
        bus.publish("signal-1", 1, 15.0, "pressure")

    status = next(iter(bus.statuses.values()))
    assert status["status"] == "publish_failed"
    bus.close()


def test_invalid_ack_model_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ControllerAck.model_validate(
            {
                "command_id": "command-1",
                "signal_id": "",
                "phase": -1,
                "hold_s": 0,
                "applied": True,
                "reason": "",
                "ts_utc": "2026-11-24T10:00:00",
            }
        )
