from types import SimpleNamespace

import paho.mqtt.client as mqtt
from vyro_backend.mqtt_subscriber import LatestMessageStore, MQTTSubscriber


def make_message(topic: str, payload: bytes) -> mqtt.MQTTMessage:
    message = mqtt.MQTTMessage(topic=topic.encode("utf-8"))
    message._topic = topic.encode("utf-8")
    message.payload = payload
    return message


def test_mqtt_message_reception_stores_payload() -> None:
    subscriber = MQTTSubscriber()
    message = make_message("vyro/v1/vehicle/state", b'{"vehicle_id":"vehicle-1"}')

    subscriber._on_mqtt_message(subscriber.client, None, message)

    assert subscriber.get_latest("vyro/v1/vehicle/state") == b'{"vehicle_id":"vehicle-1"}'


def test_latest_message_per_topic_replaces_previous_value() -> None:
    store = LatestMessageStore()
    store.put("vyro/v1/vehicle/state", b"first")
    store.put("vyro/v1/vehicle/state", b"second")

    assert store.get("vyro/v1/vehicle/state") == b"second"


def test_multiple_topics_are_stored_independently() -> None:
    subscriber = MQTTSubscriber()
    subscriber._on_mqtt_message(
        subscriber.client,
        None,
        make_message("vyro/v1/vehicle/state", b"vehicle"),
    )
    subscriber._on_mqtt_message(
        subscriber.client,
        None,
        make_message("vyro/v1/intersection/state", b"intersection"),
    )

    assert subscriber.latest_messages == {
        "vyro/v1/vehicle/state": b"vehicle",
        "vyro/v1/intersection/state": b"intersection",
    }


def test_entity_messages_are_retained_independently_per_topic() -> None:
    store = LatestMessageStore()
    store.put("vyro/v1/vehicle/state", b"vehicle-1", "vehicle-1")
    store.put("vyro/v1/vehicle/state", b"vehicle-2", "vehicle-2")

    assert store.get_entities("vyro/v1/vehicle/state") == {
        "vehicle-1": b"vehicle-1",
        "vehicle-2": b"vehicle-2",
    }


def test_connection_state_tracks_connect_and_disconnect() -> None:
    subscriber = MQTTSubscriber()
    subscriber._on_connect(
        subscriber.client,
        None,
        SimpleNamespace(),
        SimpleNamespace(is_failure=False),
        None,
    )
    assert subscriber.connected is True

    subscriber._on_disconnect(
        subscriber.client,
        None,
        SimpleNamespace(),
        SimpleNamespace(is_failure=True),
        None,
    )
    assert subscriber.connected is False
