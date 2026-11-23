import time
from datetime import UTC, datetime

from vyro_backend.command_bus import CommandBus
from vyro_backend.schemas import ControllerAck


def test_command_bus_publishes_batch_with_v11_ids_and_ack_cancels_fallback() -> None:
    published = []
    bus = CommandBus(published.append, timeout_s=0.1)

    commands = bus.publish_batch(
        [
            {"intersection_id": "intersection-1", "phase_id": 2, "reason": "pressure"},
            {"intersection_id": "intersection-2", "phase_id": 1, "reason": "pressure"},
        ]
    )

    assert [command.intersection_id for command in commands] == [
        "intersection-1",
        "intersection-2",
    ]
    assert all(command.command_id for command in commands)
    ack = ControllerAck(
        command_id=commands[0].command_id,
        intersection_id="intersection-1",
        applied=True,
        reason="applied",
        timestamp=datetime.now(UTC),
    )
    assert bus.acknowledge(ack)
    time.sleep(0.15)
    assert bus.fallback_count == 1
    bus.close()


def test_command_bus_fallback_is_counted_when_ack_never_arrives() -> None:
    bus = CommandBus(lambda command: None, timeout_s=0.01)

    bus.publish("intersection-1", 2, "pressure")
    time.sleep(0.03)

    assert bus.fallback_count == 1
    bus.close()
