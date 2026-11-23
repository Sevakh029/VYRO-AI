from typing import Protocol

from .schemas import VehicleAdvisory


class AdvisoryMQTTPublisher(Protocol):
    def publish(
        self,
        topic: str,
        payload: str,
        qos: int,
    ) -> object: ...


def advisory_topic(vehicle_id: str) -> str:
    if not vehicle_id:
        raise ValueError("vehicle_id must not be empty")
    return f"vyro/vehicle/{vehicle_id}/advisory"


class AdvisoryPublisher:
    def __init__(self, publisher: AdvisoryMQTTPublisher) -> None:
        self.publisher = publisher

    def publish(self, advisory: VehicleAdvisory) -> object:
        return self.publisher.publish(
            advisory_topic(advisory.vehicle_id),
            advisory.model_dump_json(),
            qos=1,
        )
