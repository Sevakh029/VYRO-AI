"""Transport-independent controller types and signal configuration parsing."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Action:
    """A requested hold of a configured signal phase."""

    signal_id: str
    phase: int
    hold_s: float
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.signal_id, str) or not self.signal_id.strip():
            raise ValueError("signal_id must not be empty")
        if isinstance(self.phase, bool) or not isinstance(self.phase, int) or self.phase < 0:
            raise ValueError("phase must be a non-negative integer")
        if (
            isinstance(self.hold_s, bool)
            or not isinstance(self.hold_s, (int, float))
            or not float(self.hold_s) > 0
            or float(self.hold_s) == float("inf")
        ):
            raise ValueError("hold_s must be a finite positive duration")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must not be empty")


@dataclass(frozen=True)
class PhaseConfig:
    """Safety and pressure metadata for one configured phase."""

    phase: int
    min_green_s: float
    yellow_s: float = 0.0
    all_red_s: float = 0.0
    max_wait_s: float | None = None
    detector_ids: tuple[str, ...] = ()
    weight: float = 1.0
    allowed_next: tuple[int, ...] | None = None


@dataclass(frozen=True)
class SignalConfig:
    """Trusted signal configuration used by pure controller decisions."""

    signal_id: str
    phases: tuple[PhaseConfig, ...]
    phase_order: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.signal_id, str) or not self.signal_id.strip():
            raise ValueError("signal_id must not be empty")
        if not self.phases:
            raise ValueError("signal must define at least one phase")


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite")
    if positive and result <= 0:
        raise ValueError(f"{name} must be positive")
    if not positive and result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def parse_signals_config(raw: Mapping[str, Any]) -> dict[str, SignalConfig]:
    """Parse the trusted signals.json-shaped mapping without performing file I/O."""
    if not isinstance(raw, Mapping):
        raise ValueError("signals configuration must be a mapping")

    signal_entries = raw.get("signals", raw)
    if not isinstance(signal_entries, Mapping):
        raise ValueError("signals must be a mapping")

    parsed: dict[str, SignalConfig] = {}
    for signal_id, signal_raw in signal_entries.items():
        if not isinstance(signal_raw, Mapping):
            raise ValueError(f"configuration for signal {signal_id!r} must be a mapping")

        phase_entries = signal_raw.get("phases", signal_raw.get("phase_config", {}))
        phases: list[PhaseConfig] = []
        if isinstance(phase_entries, Mapping):
            iterable = [
                (phase_key, phase_raw)
                for phase_key, phase_raw in phase_entries.items()
                if isinstance(phase_raw, Mapping)
            ]
        elif isinstance(phase_entries, list):
            iterable = [
                (
                    phase_raw.get("phase", phase_raw.get("phase_id")),
                    phase_raw,
                )
                for phase_raw in phase_entries
                if isinstance(phase_raw, Mapping)
            ]
        else:
            raise ValueError(f"phases for signal {signal_id!r} must be a mapping or list")

        for phase_key, phase_raw in iterable:
            if isinstance(phase_key, str):
                phase = int(phase_key)
            elif isinstance(phase_key, int) and not isinstance(phase_key, bool):
                phase = phase_key
            else:
                raise ValueError("phase identifiers must be integers")

            detector_value = phase_raw.get("detectors", phase_raw.get("detector_ids", []))
            detector_ids = (
                tuple(str(item) for item in detector_value)
                if isinstance(detector_value, (list, tuple))
                else ()
            )
            allowed = phase_raw.get("allowed_next")
            allowed_next = (
                tuple(int(item) for item in allowed)
                if isinstance(allowed, (list, tuple))
                else None
            )
            max_wait = phase_raw.get("max_wait_s")
            phases.append(
                PhaseConfig(
                    phase=phase,
                    min_green_s=_number(
                        phase_raw.get("min_green_s", phase_raw.get("min_green", 0)),
                        "min_green_s",
                    ),
                    yellow_s=_number(
                        phase_raw.get("yellow_s", phase_raw.get("yellow", 0)),
                        "yellow_s",
                    ),
                    all_red_s=_number(
                        phase_raw.get("all_red_s", phase_raw.get("all_red", 0)),
                        "all_red_s",
                    ),
                    max_wait_s=(
                        None
                        if max_wait is None
                        else _number(max_wait, "max_wait_s", positive=True)
                    ),
                    detector_ids=detector_ids,
                    weight=_number(phase_raw.get("weight", 1), "weight", positive=True),
                    allowed_next=allowed_next,
                )
            )

        if not phases:
            raise ValueError(f"signal {signal_id!r} must define at least one phase")
        order = tuple(
            int(item)
            for item in signal_raw.get(
                "phase_order",
                [phase.phase for phase in phases],
            )
        )
        parsed[str(signal_id)] = SignalConfig(str(signal_id), tuple(phases), order)
    return parsed


# Common import names for callers that receive parsed JSON rather than a file path.
read_signals_config = parse_signals_config
load_signals_config = parse_signals_config
