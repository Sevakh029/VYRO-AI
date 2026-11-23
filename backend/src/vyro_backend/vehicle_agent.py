import math
import random

from .schemas import VehicleState


class VehicleAgent:
    def __init__(self, vehicle_id: str) -> None:
        self.vehicle_id = vehicle_id
        self.latest_state: VehicleState | None = None

    def update(self, state: VehicleState) -> VehicleState:
        self.latest_state = state
        return state

    def neighbours(self, agents: dict[str, "VehicleAgent"], radius_m: float) -> list[str]:
        if self.latest_state is None:
            return []
        return [
            agent_id
            for agent_id, agent in agents.items()
            if agent_id != self.vehicle_id
            and agent.latest_state is not None
            and haversine_m(self.latest_state, agent.latest_state) <= radius_m
        ]


class VehicleAgentRunner:
    def __init__(
        self,
        penetration: float = 0.30,
        radius_m: float = 200.0,
        seed: int = 100,
    ) -> None:
        if not 0.0 <= penetration <= 1.0:
            raise ValueError("penetration must be between 0 and 1")
        self.penetration = penetration
        self.radius_m = radius_m
        self._random = random.Random(seed)
        self.agents: dict[str, VehicleAgent] = {}

    def receive(self, state: VehicleState) -> list[str] | None:
        if state.vehicle_id not in self.agents:
            if self._random.random() > self.penetration:
                return None
            self.agents[state.vehicle_id] = VehicleAgent(state.vehicle_id)

        agent = self.agents[state.vehicle_id]
        agent.update(state)
        return agent.neighbours(self.agents, self.radius_m)

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {
            vehicle_id: (
                agent.latest_state.model_dump(mode="json")
                if agent.latest_state is not None
                else {}
            )
            for vehicle_id, agent in self.agents.items()
        }


def haversine_m(first: VehicleState, second: VehicleState) -> float:
    first_lat = math.radians(first.latitude)
    second_lat = math.radians(second.latitude)
    latitude_delta = second_lat - first_lat
    longitude_delta = math.radians(second.longitude - first.longitude)
    value = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(first_lat) * math.cos(second_lat) * math.sin(longitude_delta / 2) ** 2
    )
    return 6371000.0 * 2 * math.asin(min(1.0, math.sqrt(value)))
