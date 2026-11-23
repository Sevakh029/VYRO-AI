import argparse
import logging
import os
import random
import time
from datetime import UTC, datetime
from threading import Event

import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from .publish_path import PublishPath
from .schemas import VehicleState

logger = logging.getLogger(__name__)

VEHICLE_COUNT = 200
PUBLISH_INTERVAL_SECONDS = 1.0
VEHICLE_STATE_TOPIC = "vyro/v1/vehicle/state"


class FakeVehicleGenerator:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 1883,
        client_id: str = "vyro-fake-vehicle-generator",
        client: mqtt.Client | None = None,
        publish_path: PublishPath | None = None,
        penetration: float = 1.0,
        seed: int = 100,
        vehicle_type: str = "car",
    ) -> None:
        self._client = client or mqtt.Client(
            CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.host = host
        self.port = port
        self._connected = Event()
        self._tick = 0
        self.publish_path = publish_path or PublishPath()
        if not 0.0 <= penetration <= 1.0:
            raise ValueError("penetration must be between 0 and 1")
        self.penetration = penetration
        self._random = random.Random(seed)
        self.vehicle_type = vehicle_type
        self.vehicle_ids = tuple(
            f"fake-vehicle-{index:04d}" for index in range(1, VEHICLE_COUNT + 1)
        )

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        del client, userdata, flags, properties
        if reason_code.is_failure:
            self._connected.clear()
            logger.error("MQTT connection failed: %s", reason_code)
            return
        self._connected.set()
        logger.info("Connected to MQTT broker at %s:%s", self.host, self.port)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        del client, userdata, disconnect_flags, properties
        self._connected.clear()
        if reason_code.is_failure:
            logger.warning("MQTT disconnected unexpectedly: %s; reconnecting", reason_code)
        else:
            logger.info("Disconnected from MQTT broker")

    def start(self) -> None:
        self._client.connect_async(self.host, self.port)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()
        self.publish_path.close()

    def generate_states(self, timestamp: datetime | None = None) -> tuple[VehicleState, ...]:
        current_timestamp = timestamp or datetime.now(UTC)
        movement_offset = (self._tick % 10_000) * 0.000001
        self._tick += 1
        return tuple(
            VehicleState(
                vehicle_id=vehicle_id,
                latitude=40.1 + (index % 20) * 0.001 + movement_offset,
                longitude=44.4 + (index // 20) * 0.001,
                speed_mps=(index % 25) * 0.5,
                heading_deg=float(index % 360),
                timestamp=current_timestamp,
                vehicle_type=self.vehicle_type,
            )
            for index, vehicle_id in enumerate(self.vehicle_ids)
        )

    def publish_once(self) -> int:
        if not self._connected.is_set():
            logger.warning("Skipping vehicle-state cycle while MQTT is disconnected")
            return 0

        published = 0
        for state in self.generate_states():
            if self._random.random() > self.penetration:
                continue
            try:
                result = self.publish_path.publish(
                    lambda state=state: self._client.publish(
                        VEHICLE_STATE_TOPIC,
                        state.model_dump_json(),
                        qos=1,
                    )
                )
            except (OSError, MQTTException) as exc:
                logger.error("Failed to publish state for %s: %s", state.vehicle_id, exc)
                continue
            if result is False:
                continue
            if result is None:
                published += 1
                continue
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(
                    "Failed to publish state for %s: MQTT result %s",
                    state.vehicle_id,
                    result.rc,
                )
                continue
            published += 1
        return published

    def run_forever(self, stop_event: Event) -> None:
        next_publish_at = time.monotonic()
        while not stop_event.is_set():
            self.publish_once()
            next_publish_at += PUBLISH_INTERVAL_SECONDS
            now = time.monotonic()
            if now > next_publish_at:
                next_publish_at = now
            if stop_event.wait(max(0.0, next_publish_at - now)):
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish 200 fake VYRO vehicle states at 1 Hz")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--jitter-seconds", type=float, default=0.0)
    parser.add_argument("--drop-probability", type=float, default=0.0)
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"))
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"))
    parser.add_argument("--penetration", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--vehicle-type", default="car")
    args = parser.parse_args()

    publish_path = PublishPath(
        delay_seconds=args.delay_seconds,
        jitter_seconds=args.jitter_seconds,
        drop_probability=args.drop_probability,
    )
    generator = FakeVehicleGenerator(
        host=args.host,
        port=args.port,
        publish_path=publish_path,
        penetration=args.penetration,
        seed=args.seed,
        vehicle_type=args.vehicle_type,
    )
    if args.username is not None:
        generator._client.username_pw_set(args.username, args.password)
    try:
        generator.start()
        generator.run_forever(Event())
    except KeyboardInterrupt:
        logger.info("Stopping fake-vehicle generator")
    finally:
        generator.stop()


if __name__ == "__main__":
    main()
