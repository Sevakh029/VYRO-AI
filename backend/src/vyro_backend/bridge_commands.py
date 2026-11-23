import logging

from pydantic import ValidationError

from .mqtt_subscriber import MQTTSubscriber
from .schemas import SignalCommand

logger = logging.getLogger(__name__)

COMMAND_TOPIC = "vyro/v1/controller/command"


class BridgeCommandSubscriber:
    def __init__(self, subscriber: MQTTSubscriber) -> None:
        self.subscriber = subscriber
        self.commands: dict[str, SignalCommand] = {}
        subscriber._on_message = self.receive

    def receive(self, topic: str, payload: bytes) -> bool | str:
        if topic != COMMAND_TOPIC:
            return True
        try:
            command = SignalCommand.model_validate_json(payload)
        except ValidationError:
            logger.warning("Rejected invalid bridge command")
            return False
        self.commands[command.intersection_id] = command
        logger.info(
            "Bridge received command for intersection %s, phase %d",
            command.intersection_id,
            command.phase_id,
        )
        return command.intersection_id
