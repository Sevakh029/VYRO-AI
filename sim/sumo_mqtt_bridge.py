"""Bridge live TraCI vehicle positions to the VYRO MQTT vehicle-state topic."""

import argparse
import json
import os
import time
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
from pydantic import ValidationError
from vyro_backend.schemas import (
    ControllerAck,
    IntersectionState,
    SignalCommand,
    VehicleState,
)

VEHICLE_STATE_TOPIC = "vyro/v1/vehicle/state"
INTERSECTION_STATE_TOPIC = "vyro/v1/intersection/state"
COMMAND_TOPIC = "vyro/v1/controller/command"
ACK_TOPIC = "vyro/v1/controller/ack"
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
        signals_file: Path | None = None,
        fixed_fallback_s: float = 30.0,
    ) -> None:
        self.projection = projection
        self.client = client
        self.vehicle_type = vehicle_type
        self.signals_file = signals_file
        self.fixed_fallback_s = fixed_fallback_s
        self._signals = self._load_signals(signals_file)
        self._traci: Any | None = None
        self._last_valid_command: dict[str, float] = {}
        self._fixed_program = "0"
        self.connected = False
        self._connection_result = Event()
        self._connection_error: str | None = None

    @staticmethod
    def _load_signals(signals_file: Path | None) -> dict[str, dict[str, object]]:
        if signals_file is None:
            return {}
        data = json.loads(signals_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("signals"), list):
            raise ValueError("signals.json must contain a signals array")
        result: dict[str, dict[str, object]] = {}
        for raw in data["signals"]:
            if not isinstance(raw, dict) or not isinstance(raw.get("signal_id"), str):
                raise ValueError("invalid signal configuration")
            result[str(raw["signal_id"])] = raw
        return result

    def attach_traci(self, traci: Any) -> None:
        self._traci = traci

    def on_command(self, client: mqtt.Client, userdata: object, message: mqtt.MQTTMessage) -> None:
        del client, userdata
        try:
            command = SignalCommand.model_validate_json(bytes(message.payload))
        except (ValidationError, UnicodeDecodeError, ValueError) as exc:
            del exc
            return
        self.apply_command(command)

    def apply_command(self, command: SignalCommand) -> ControllerAck:
        reason = "applied"
        applied = False
        config = self._signals.get(command.signal_id)
        if config is None:
            reason = "unknown signal_id"
        else:
            phases = config.get("phases")
            valid = isinstance(phases, list) and any(
                isinstance(phase, dict)
                and phase.get("phase") == command.phase
                for phase in phases
            )
            if not valid:
                reason = "phase is not configured for signal"
            elif self._traci is None:
                reason = "TraCI bridge is not attached"
            else:
                try:
                    tls_ids = tuple(self._traci.trafficlight.getIDList())
                    if command.signal_id not in tls_ids:
                        reason = "signal_id is not present in TraCI"
                    else:
                        self._traci.trafficlight.setPhase(command.signal_id, command.phase)
                        actual_phase = int(
                            self._traci.trafficlight.getPhase(command.signal_id)
                        )
                        if actual_phase != command.phase:
                            reason = "TraCI did not apply the requested phase"
                        else:
                            applied = True
                            self._last_valid_command[command.signal_id] = time.monotonic()
                except Exception as exc:
                    reason = f"TraCI command failed: {type(exc).__name__}"
                    del exc
        ack = ControllerAck(
            command_id=command.command_id,
            signal_id=command.signal_id,
            phase=command.phase,
            hold_s=command.hold_s,
            applied=applied,
            reason=reason,
            ts_utc=datetime.now(UTC),
        )
        if self.connected:
            self.client.publish(ACK_TOPIC, ack.model_dump_json(), qos=1)
        return ack

    def check_fixed_time_fallback(self, traci: Any) -> int:
        if traci is None:
            return 0
        reverted = 0
        now = time.monotonic()
        for signal_id in tuple(traci.trafficlight.getIDList()):
            last_valid = self._last_valid_command.get(signal_id)
            if last_valid is not None and now - last_valid <= self.fixed_fallback_s:
                continue
            try:
                traci.trafficlight.setProgram(signal_id, self._fixed_program)
                self._last_valid_command.pop(signal_id, None)
                reverted += 1
            except Exception:
                continue
        return reverted

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
                if hasattr(client, "message_callback_add"):
                    client.message_callback_add(COMMAND_TOPIC, self.on_command)
                if hasattr(client, "subscribe"):
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

    def publish_intersections(
        self,
        traci: Any,
        timestamp: datetime | None = None,
    ) -> int:
        if not self.connected:
            return 0
        current_timestamp = timestamp or datetime.now(UTC)
        published = 0
        vehicle_lane_ids: dict[str, int] = {}
        for vehicle_id in traci.vehicle.getIDList():
            lane_id = str(traci.vehicle.getLaneID(vehicle_id))
            vehicle_lane_ids[lane_id] = vehicle_lane_ids.get(lane_id, 0) + 1
        for signal_id in traci.trafficlight.getIDList():
            controlled_lanes = tuple(
                dict.fromkeys(
                    str(lane_id)
                    for lane_id in traci.trafficlight.getControlledLanes(signal_id)
                )
            )
            detector_counts = {
                lane_id: vehicle_lane_ids.get(lane_id, 0)
                for lane_id in controlled_lanes
            }
            state = IntersectionState(
                intersection_id=signal_id,
                phase_id=int(traci.trafficlight.getPhase(signal_id)),
                time_in_phase_s=float(traci.trafficlight.getSpentTime(signal_id)),
                detector_counts=detector_counts,
                timestamp=current_timestamp,
            )
            result = self.client.publish(
                INTERSECTION_STATE_TOPIC,
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
    signals_file = Path(__file__).resolve().parent / "signals.json"
    bridge = SumoMqttBridge(
        projection,
        client,
        signals_file=signals_file,
    )
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
        bridge.attach_traci(traci)
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            bridge.publish_positions(traci)
            bridge.publish_intersections(traci)
            bridge.check_fixed_time_fallback(traci)
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
