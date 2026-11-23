from vyro_backend.bridge_commands import COMMAND_TOPIC, BridgeCommandSubscriber
from vyro_backend.mqtt_subscriber import MQTTSubscriber


def test_bridge_command_subscriber_validates_and_logs_commands() -> None:
    subscriber = MQTTSubscriber()
    bridge = BridgeCommandSubscriber(subscriber)
    payload = (
        b'{"intersection_id":"intersection-1","phase_id":2,'
        b'"reason":"queue_pressure","timestamp":"2026-11-23T10:00:00Z"}'
    )

    assert bridge.receive(COMMAND_TOPIC, payload) == "intersection-1"
    assert "intersection-1" in bridge.commands


def test_bridge_command_subscriber_rejects_malformed_commands() -> None:
    subscriber = MQTTSubscriber()
    bridge = BridgeCommandSubscriber(subscriber)

    assert bridge.receive(COMMAND_TOPIC, b"{malformed") is False
