import argparse
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish a VYRO MQTT hello message")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="vyro/v1/hello")
    args = parser.parse_args()

    client = mqtt.Client(CallbackAPIVersion.VERSION2)
    client.connect(args.host, args.port)
    client.loop_start()
    time.sleep(0.1)
    result = client.publish(args.topic, "hello from VYRO", qos=1)
    result.wait_for_publish(timeout=2)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
