import argparse

import paho.mqtt.client as mqtt


def on_connect(
    client: mqtt.Client,
    userdata: object,
    flags: mqtt.ConnectFlags,
    reason_code: mqtt.ReasonCode,
    properties: mqtt.Properties | None,
) -> None:
    del userdata, flags, properties
    if reason_code.is_failure:
        print(f"MQTT connection failed: {reason_code}")
        return
    client.subscribe("vyro/v1/#", qos=1)


def on_message(client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
    del client, userdata
    print(f"{message.topic}: {message.payload.decode('utf-8', errors='replace')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Subscribe to VYRO MQTT messages")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.host, args.port)
    client.loop_forever()


if __name__ == "__main__":
    main()
