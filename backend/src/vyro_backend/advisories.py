from typing import Protocol

from .schemas import VehicleAdvisory

ADVISORY_TOPIC = "vyro/v1/vehicle/advisory"


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
    del vehicle_id
    return ADVISORY_TOPIC


class AdvisoryPublisher:
    def __init__(self, publisher: AdvisoryMQTTPublisher) -> None:
        self.publisher = publisher

    def publish(self, advisory: VehicleAdvisory) -> object:
        return self.publisher.publish(
            advisory_topic(advisory.vehicle_id),
            advisory.model_dump_json(),
            qos=1,
        )
