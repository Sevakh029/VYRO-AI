"""Bridge live TraCI vehicle positions to the VYRO MQTT vehicle-state topic."""

import argparse
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode
from vyro_backend.schemas import VehicleState

VEHICLE_STATE_TOPIC = "vyro/v1/vehicle/state"
MQTT_CONNECT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class NetworkProjection:
    convert_xy_to_lonlat: Callable[[float, float], tuple[float, float]]

    def position_to_latlon(self, x: float, y: float) -> tuple[float, float]:
        longitude, latitude = self.convert_xy_to_lonlat(x, y)
        return latitude, longitude


class SumoMqttBridge:
    def __init__(
        self,
        projection: NetworkProjection,
        client: mqtt.Client,
        vehicle_type: str = "unknown",
    ) -> None:
        self.projection = projection
        self.client = client
        self.vehicle_type = vehicle_type
        self.connected = False
        self._connection_result = Event()
        self._connection_error: str | None = None

    def wait_until_connected(self, timeout: float) -> None:
        if not self._connection_result.wait(timeout):
            raise TimeoutError("Timed out waiting for the MQTT broker connection")
        if not self.connected:
            detail = f": {self._connection_error}" if self._connection_error else ""
            raise ConnectionError(f"MQTT broker rejected the connection{detail}")

    def on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        del client, userdata, flags, properties
        if reason_code.is_failure:
            self.connected = False
            self._connection_error = str(reason_code)
        else:
            self.connected = True
            self._connection_error = None
        self._connection_result.set()

    def on_disconnect(
        self,
        client: mqtt.Client,
        userdata: object,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        del client, userdata, disconnect_flags, reason_code, properties
        self.connected = False

    def publish_positions(self, traci: Any, timestamp: datetime | None = None) -> int:
        if not self.connected:
            return 0
        published = 0
        current_timestamp = timestamp or datetime.now(UTC)
        for vehicle_id in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vehicle_id)
            latitude, longitude = self.projection.position_to_latlon(x, y)
            speed = float(traci.vehicle.getSpeed(vehicle_id))
            heading = float(traci.vehicle.getAngle(vehicle_id))
            state = VehicleState(
                vehicle_id=vehicle_id,
                latitude=latitude,
                longitude=longitude,
                speed_mps=max(0.0, speed),
                heading_deg=heading % 360.0,
                timestamp=current_timestamp,
                vehicle_type=self.vehicle_type,
            )
            result = self.client.publish(
                VEHICLE_STATE_TOPIC,
                state.model_dump_json(),
                qos=1,
            )
            if getattr(result, "rc", mqtt.MQTT_ERR_SUCCESS) == mqtt.MQTT_ERR_SUCCESS:
                published += 1
        return published


def load_network(network_file: Path) -> Any:
    import sumolib

    return sumolib.net.readNet(str(network_file), withPrograms=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish TraCI vehicle positions over MQTT")
    parser.add_argument("network", type=Path)
    parser.add_argument("routes", type=Path)
    parser.add_argument("--sumo-home", default=os.getenv("SUMO_HOME"))
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--step-length", type=float, default=1.0)
    args = parser.parse_args()

    if not args.sumo_home:
        raise RuntimeError("SUMO_HOME is not set")

    network = load_network(args.network)
    projection = NetworkProjection(network.convertXY2LonLat)
    sumo_binary = Path(args.sumo_home) / "bin" / (
        "sumo.exe" if os.name == "nt" else "sumo"
    )
    import traci

    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="vyro-sumo-mqtt-bridge")
    bridge = SumoMqttBridge(projection, client)
    client.on_connect = bridge.on_connect
    client.on_disconnect = bridge.on_disconnect
    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")
    if not username or not password:
        raise RuntimeError("MQTT_USERNAME and MQTT_PASSWORD are required")
    client.username_pw_set(username, password)
    client.connect(args.host, args.port)
    traci_started = False
    loop_started = False
    try:
        client.loop_start()
        loop_started = True
        bridge.wait_until_connected(MQTT_CONNECT_TIMEOUT_SECONDS)
        traci.start([
            str(sumo_binary),
            "--net-file", str(args.network),
            "--route-files", str(args.routes),
            "--step-length", str(args.step_length),
            "--start",
        ])
        traci_started = True
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            bridge.publish_positions(traci)
    finally:
        try:
            if traci_started:
                traci.close()
        finally:
            client.disconnect()
            if loop_started:
                client.loop_stop()


if __name__ == "__main__":
    main()
