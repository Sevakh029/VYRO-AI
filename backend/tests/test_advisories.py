from datetime import UTC, datetime

from vyro_backend.advisories import AdvisoryPublisher, advisory_topic
from vyro_backend.schemas import VehicleAdvisory


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def publish(self, topic: str, payload: str, qos: int) -> str:
        self.calls.append((topic, payload, qos))
        return "published"


def test_advisory_publisher_uses_per_vehicle_topic() -> None:
    publisher = FakePublisher()
    advisory = VehicleAdvisory(
        vehicle_id="vehicle-42",
        advisory_type="risk",
        message="Collision risk",
        timestamp=datetime(2026, 11, 23, tzinfo=UTC),
    )

    result = AdvisoryPublisher(publisher).publish(advisory)

    assert result == "published"
    assert advisory_topic("vehicle-42") == "vyro/vehicle/vehicle-42/advisory"
    assert publisher.calls[0][0] == "vyro/vehicle/vehicle-42/advisory"
    assert publisher.calls[0][2] == 1
