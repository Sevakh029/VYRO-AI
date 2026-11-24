from threading import Lock

from pydantic import BaseModel

from .schemas import IntersectionState, SignalCommand, VehicleState


class ScenarioState(BaseModel):
    name: str = "normal"
    status: str = "stopped"


class InMemoryTrafficState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._vehicles: dict[str, VehicleState] = {}
        self._intersections: dict[str, IntersectionState] = {}
        self._commands: dict[str, SignalCommand] = {}
        self._scenario = ScenarioState()

    def receive_vehicle(self, message: VehicleState) -> None:
        with self._lock:
            self._vehicles[message.vehicle_id] = message

    def receive_intersection(self, message: IntersectionState) -> None:
        with self._lock:
            self._intersections[message.intersection_id] = message

    def receive_command(self, message: SignalCommand) -> None:
        with self._lock:
            self._commands[message.intersection_id] = message

    def set_scenario(self, name: str, status: str) -> None:
        with self._lock:
            self._scenario = ScenarioState(name=name, status=status)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "vehicles": {
                    key: value.model_dump(mode="json")
                    for key, value in self._vehicles.items()
                },
                "intersections": {
                    key: value.model_dump(mode="json")
                    for key, value in self._intersections.items()
                },
                "commands": {
                    key: value.model_dump(mode="json")
                    for key, value in self._commands.items()
                },
                "scenario": self._scenario.model_dump(mode="json"),
            }
