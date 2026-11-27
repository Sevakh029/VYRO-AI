"""Bridge live TraCI vehicle positions to the VYRO MQTT vehicle-state topic."""

import argparse
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode
from pydantic import ValidationError
from vyro_backend.schemas import ControllerAck, SignalCommand, VehicleState
from vyro_backend.timestamps import utc_now

VEHICLE_STATE_TOPIC = "vyro/v1/vehicle/state"
COMMAND_TOPIC = "vyro/v1/controller/command"
ACK_TOPIC = "vyro/v1/controller/ack"
MQTT_CONNECT_TIMEOUT_SECONDS = 10.0


def load_signals_config(signals_file: Path) -> dict[str, tuple[int, ...]]:
    if not signals_file.is_file():
        raise FileNotFoundError(f"Signals configuration does not exist: {signals_file}")
    data = json.loads(signals_file.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("signals.json must contain a JSON array")

    signals: dict[str, tuple[int, ...]] = {}
    for record in data:
        if not isinstance(record, dict):
            raise ValueError("each signals.json record must be a JSON object")
        signal_id = record.get("signal_id")
        valid_indices = record.get("valid_phase_indices")
        if not isinstance(signal_id, str) or not signal_id:
            raise ValueError("each signal requires a non-empty signal_id")
        if not isinstance(valid_indices, list):
            raise ValueError(f"signal {signal_id} requires valid_phase_indices")
        if any(
            isinstance(index, bool) or not isinstance(index, int) or index < 0
            for index in valid_indices
        ):
            raise ValueError(f"signal {signal_id} has invalid valid_phase_indices")
        if signal_id in signals:
            raise ValueError(f"duplicate signal_id in signals.json: {signal_id}")
        signals[signal_id] = tuple(valid_indices)
    return signals


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
        signals_file: Path | str | None = None,
    ) -> None:
        self.projection = projection
        self.client = client
        self.vehicle_type = vehicle_type
        self.connected = False
        self._connection_result = Event()
        self._connection_error: str | None = None
        if signals_file is None:
            signals_file = Path(__file__).resolve().parents[1] / "signals.json"
        try:
            self.signals = load_signals_config(Path(signals_file))
        except FileNotFoundError:
            self.signals = {}
        self._traci: Any | None = None
        self._pending_commands: list[bytes] = []

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
        del userdata, flags, properties
        if reason_code.is_failure:
            self.connected = False
            self._connection_error = str(reason_code)
        else:
            self.connected = True
            self._connection_error = None
            if client is not None:
                client.subscribe(COMMAND_TOPIC, qos=1)
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

    def on_message(
        self,
        client: mqtt.Client,
        userdata: object,
        message: Any,
    ) -> None:
        del client, userdata
        topic = getattr(message, "_topic", getattr(message, "topic", None))
        if isinstance(topic, bytes):
            topic = topic.decode("utf-8")
        if str(topic) != COMMAND_TOPIC:
            return
        payload = bytes(message.payload)
        self._pending_commands.append(payload)

    def set_traci(self, traci: Any) -> None:
        self._traci = traci

    def process_pending_commands(self) -> int:
        processed = 0
        if self._traci is None:
            return processed
        while self._pending_commands:
            payload = self._pending_commands.pop(0)
            self.apply_phase_command(self._traci, payload)
            processed += 1
        return processed

    def apply_phase_command(
        self,
        traci: Any,
        payload: SignalCommand | bytes | dict[str, Any],
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        try:
            if isinstance(payload, SignalCommand):
                command = payload
            elif isinstance(payload, bytes):
                command = SignalCommand.model_validate_json(payload)
            else:
                command = SignalCommand.model_validate(payload)
        except ValidationError:
            return {
                "applied": False,
                "reason": "invalid command",
                "command_id": "",
                "intersection_id": "",
            }

        signal_id = command.intersection_id
        valid_indices = self.signals.get(signal_id)
        if valid_indices is None:
            return self._publish_rejection(
                command,
                f"unknown signal: {signal_id}",
                timestamp,
            )
        if command.phase_id not in valid_indices:
            return self._publish_rejection(
                command,
                f"invalid phase index {command.phase_id} for signal {signal_id}",
                timestamp,
            )

        traci.trafficlight.setPhase(signal_id, command.phase_id)
        return self._publish_ack(
            command,
            True,
            "phase applied",
            timestamp,
        )

    def _publish_rejection(
        self,
        command: SignalCommand,
        reason: str,
        timestamp: datetime | None,
    ) -> dict[str, Any]:
        return self._publish_ack(command, False, reason, timestamp)

    def _publish_ack(
        self,
        command: SignalCommand,
        applied: bool,
        reason: str,
        timestamp: datetime | None,
    ) -> dict[str, Any]:
        command_id = command.command_id or f"bridge-{command.timestamp.isoformat()}"
        ack = ControllerAck(
            command_id=command_id,
            intersection_id=command.intersection_id,
            applied=applied,
            reason=reason,
            timestamp=timestamp or utc_now(),
        )
        if self.connected:
            self.client.publish(ACK_TOPIC, ack.model_dump_json(), qos=1)
        return {
            "command_id": command_id,
            "intersection_id": command.intersection_id,
            "phase_id": command.phase_id,
            "applied": applied,
            "reason": reason,
        }

    def publish_positions(self, traci: Any, timestamp: datetime | None = None) -> int:
        if not self.connected:
            return 0
        published = 0
        current_timestamp = timestamp or utc_now()
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
    parser.add_argument(
        "--signals",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "signals.json",
    )
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
    bridge = SumoMqttBridge(projection, client, signals_file=args.signals)
    client.on_connect = bridge.on_connect
    client.on_disconnect = bridge.on_disconnect
    client.on_message = bridge.on_message
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
        bridge.set_traci(traci)
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            bridge.process_pending_commands()
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
