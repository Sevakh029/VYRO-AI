import argparse
import logging
from collections.abc import Callable
from threading import Lock

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

logger = logging.getLogger(__name__)


class LatestMessageStore:
    def __init__(self) -> None:
        self._messages: dict[str, bytes] = {}
        self._messages_by_entity: dict[str, dict[str, bytes]] = {}
        self._lock = Lock()

    def put(self, topic: str, payload: bytes, entity_id: str | None = None) -> None:
        with self._lock:
            self._messages[topic] = payload
            if entity_id is not None:
                self._messages_by_entity.setdefault(topic, {})[entity_id] = payload

    def get(self, topic: str) -> bytes | None:
        with self._lock:
            return self._messages.get(topic)

    def get_entities(self, topic: str) -> dict[str, bytes]:
        with self._lock:
            return dict(self._messages_by_entity.get(topic, {}))

    @property
    def latest(self) -> dict[str, bytes]:
        with self._lock:
            return dict(self._messages)


class MQTTSubscriber:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1883,
        topic: str = "vyro/v1/#",
        on_message: Callable[[str, bytes], bool | str | None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.topic = topic
        self.store = LatestMessageStore()
        self._on_message = on_message
        self.client = mqtt.Client(CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_mqtt_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        del userdata, flags, properties
        if reason_code.is_failure:
            logger.error("MQTT connection failed: %s", reason_code)
            return
        result, _ = client.subscribe(self.topic, qos=1)
        if result != mqtt.MQTT_ERR_SUCCESS:
            logger.error("MQTT subscription failed for %s", self.topic)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        del client, userdata, disconnect_flags, properties
        if reason_code.is_failure:
            logger.warning("MQTT disconnected unexpectedly: %s; reconnecting", reason_code)
        else:
            logger.info("MQTT disconnected")

    def _on_mqtt_message(
        self,
        client: mqtt.Client,
        userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        del client, userdata
        payload = bytes(message.payload)
        raw_topic = getattr(message, "_topic", message.topic)
        topic = (
            raw_topic.decode("utf-8")
            if isinstance(raw_topic, bytes)
            else str(raw_topic)
        )
        accepted = True
        entity_id = None
        if self._on_message is not None:
            disposition = self._on_message(topic, payload)
            accepted = disposition is not False
            if isinstance(disposition, str):
                entity_id = disposition
        if accepted:
            self.store.put(topic, payload, entity_id)

    def start(self) -> None:
        try:
            self.client.connect_async(self.host, self.port)
            self.client.loop_start()
        except (OSError, mqtt.WebsocketConnectionError) as exc:
            logger.error("Unable to start MQTT subscriber: %s", exc)

    def stop(self) -> None:
        self.client.disconnect()
        self.client.loop_stop()

    def get_latest(self, topic: str) -> bytes | None:
        return self.store.get(topic)

    @property
    def latest_messages(self) -> dict[str, bytes]:
        return self.store.latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Subscribe to VYRO MQTT messages")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()

    subscriber = MQTTSubscriber(host=args.host, port=args.port)
    subscriber.start()
    subscriber.client.loop_forever()


if __name__ == "__main__":
    main()
