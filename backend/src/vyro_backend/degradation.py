import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DegradationConfig:
    loss: float = 0.0
    latency_ms: int = 0
    jitter_ms: int = 0

    def validate(self) -> None:
        if not 0.0 <= self.loss <= 1.0:
            raise ValueError("loss must be between 0 and 1")
        if self.latency_ms < 0 or self.jitter_ms < 0:
            raise ValueError("latency and jitter must be non-negative")


def sweep_degradation(
    loss_values: tuple[float, ...] = (0.0, 0.05, 0.10, 0.20),
    latency_values_ms: tuple[int, ...] = (0, 200, 500),
    jitter_ms: int = 0,
) -> list[DegradationConfig]:
    sweep: list[DegradationConfig] = []
    for loss in loss_values:
        for latency_ms in latency_values_ms:
            config = DegradationConfig(loss=loss, latency_ms=latency_ms, jitter_ms=jitter_ms)
            config.validate()
            sweep.append(config)
    return sweep


def save_degradation_sweep(path: str | Path, configs: list[DegradationConfig]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps([config.__dict__ for config in configs], indent=2),
        encoding="utf-8",
    )
