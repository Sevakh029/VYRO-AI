"""Bridge live TraCI vehicle positions to the VYRO MQTT vehicle-state topic."""

import argparse
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from vyro_backend.schemas import VehicleState

VEHICLE_STATE_TOPIC = "vyro/v1/vehicle/state"


@dataclass(frozen=True)
class NetworkBounds:
    west: float
    south: float
    east: float
    north: float
    sumo_west: float
    sumo_south: float
    sumo_east: float
    sumo_north: float

    def position_to_latlon(self, x: float, y: float) -> tuple[float, float]:
        if self.sumo_east <= self.sumo_west or self.sumo_north <= self.sumo_south:
            raise ValueError("SUMO network bounds must be non-empty")
        longitude = self.west + (x - self.sumo_west) * (self.east - self.west) / (
            self.sumo_east - self.sumo_west
        )
        latitude = self.south + (y - self.sumo_south) * (self.north - self.south) / (
            self.sumo_north - self.sumo_south
        )
        return latitude, longitude


class SumoMqttBridge:
    def __init__(
        self,
        bounds: NetworkBounds,
        client: mqtt.Client,
        vehicle_type: str = "unknown",
    ) -> None:
        self.bounds = bounds
        self.client = client
        self.vehicle_type = vehicle_type
        self.connected = False

    def on_connect(
        self,
        client: mqtt.Client,
        userdata: object,
        flags: object,
        reason: object,
    ) -> None:
        del client, userdata, flags
        if getattr(reason, "is_failure", False):
            self.connected = False
            return
        self.connected = True

    def publish_positions(self, traci: Any, timestamp: datetime | None = None) -> int:
        if not self.connected:
            return 0
        published = 0
        current_timestamp = timestamp or datetime.now(UTC)
        for vehicle_id in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vehicle_id)
            latitude, longitude = self.bounds.position_to_latlon(x, y)
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


def load_network_bounds(network_file: Path) -> tuple[float, float, float, float]:
    import sumolib

    network = sumolib.net.readNet(str(network_file), withPrograms=True)
    boundary = network.getBoundary()
    return float(boundary[0]), float(boundary[1]), float(boundary[2]), float(boundary[3])


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish TraCI vehicle positions over MQTT")
    parser.add_argument("network", type=Path)
    parser.add_argument("routes", type=Path)
    parser.add_argument("--sumo-home", default=os.getenv("SUMO_HOME"))
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--west", type=float, required=True)
    parser.add_argument("--south", type=float, required=True)
    parser.add_argument("--east", type=float, required=True)
    parser.add_argument("--north", type=float, required=True)
    parser.add_argument("--step-length", type=float, default=1.0)
    args = parser.parse_args()

    if not args.sumo_home:
        raise RuntimeError("SUMO_HOME is not set")

    sumo_west, sumo_south, sumo_east, sumo_north = load_network_bounds(args.network)
    bounds = NetworkBounds(
        west=args.west,
        south=args.south,
        east=args.east,
        north=args.north,
        sumo_west=sumo_west,
        sumo_south=sumo_south,
        sumo_east=sumo_east,
        sumo_north=sumo_north,
    )

    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="vyro-sumo-mqtt-bridge")
    bridge = SumoMqttBridge(bounds, client)
    client.on_connect = bridge.on_connect
    client.username_pw_set(
        os.getenv("MQTT_USERNAME"),
        os.getenv("MQTT_PASSWORD"),
    )
    client.connect(args.host, args.port)
    client.loop_start()

    sumo_bin = Path(args.sumo_home) / "bin" / "sumo.exe"
    import traci

    traci.start([
        str(sumo_bin),
        "--net-file", str(args.network),
        "--route-files", str(args.routes),
        "--step-length", str(args.step_length),
        "--start",
    ])
    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            bridge.publish_positions(traci)
    finally:
        traci.close()
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
