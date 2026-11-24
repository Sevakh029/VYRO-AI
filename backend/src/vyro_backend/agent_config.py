import json
from dataclasses import dataclass
from pathlib import Path

from .publish_path import PublishPath
from .vehicle_agent import VehicleAgentRunner


@dataclass(frozen=True)
class AgentConfig:
    penetration: float = 0.30
    radius_m: float = 200.0
    seed: int = 100
    delay_seconds: float = 0.0
    jitter_seconds: float = 0.0
    drop_probability: float = 0.0

    @classmethod
    def from_json(cls, path: str | Path) -> "AgentConfig":
        with Path(path).open(encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("agent configuration must be a JSON object")
        allowed = {
            "penetration",
            "radius_m",
            "seed",
            "delay_seconds",
            "jitter_seconds",
            "drop_probability",
        }
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"unknown agent configuration fields: {sorted(unknown)}")
        config = cls(**data)
        config.validate()
        return config

    def validate(self) -> None:
        if not 0.0 <= self.penetration <= 1.0:
            raise ValueError("penetration must be between 0 and 1")
        if self.radius_m < 0:
            raise ValueError("radius_m must be non-negative")
        if self.delay_seconds < 0 or self.jitter_seconds < 0:
            raise ValueError("delay and jitter must be non-negative")
        if not 0.0 <= self.drop_probability <= 1.0:
            raise ValueError("drop_probability must be between 0 and 1")

    def create_runner(self) -> VehicleAgentRunner:
        return VehicleAgentRunner(
            penetration=self.penetration,
            radius_m=self.radius_m,
            seed=self.seed,
        )

    def create_publish_path(self) -> PublishPath:
        return PublishPath(
            delay_seconds=self.delay_seconds,
            jitter_seconds=self.jitter_seconds,
            drop_probability=self.drop_probability,
            seed=self.seed,
        )
