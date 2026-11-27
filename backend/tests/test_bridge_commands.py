from vyro_backend.bridge_commands import COMMAND_TOPIC, BridgeCommandSubscriber
from vyro_backend.mqtt_subscriber import MQTTSubscriber


def test_bridge_command_subscriber_validates_and_logs_commands() -> None:
    subscriber = MQTTSubscriber()
    bridge = BridgeCommandSubscriber(subscriber)
    payload = (
        b'{"command_id":"command-1","signal_id":"signal-1","phase":2,'
        b'"hold_s":15.0,"reason":"queue_pressure","ts_utc":"2026-11-23T10:00:00Z"}'
    )

    assert bridge.receive(COMMAND_TOPIC, payload) == "signal-1"
    assert "signal-1" in bridge.commands


def test_bridge_command_subscriber_rejects_malformed_commands() -> None:
    subscriber = MQTTSubscriber()
    bridge = BridgeCommandSubscriber(subscriber)

    assert bridge.receive(COMMAND_TOPIC, b"{malformed") is False
