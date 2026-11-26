"""Generate a Webster-timed SUMO additional file from a static network program."""

import argparse
import json
import math
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import sumolib
from vyro_controller.webster import PhaseFlow, calculate_webster_plan

PhaseKey = tuple[str, str, int]


@dataclass(frozen=True)
class PhaseDemandSettings:
    flow_veh_per_hour: float
    saturation_flow_veh_per_hour: float = 1800.0
    minimum_green_s: float = 5.0


def load_phase_demands(
    path: Path,
    seed: int | None = None,
) -> dict[PhaseKey, PhaseDemandSettings]:
    """Load per-green-phase demand records from a JSON array."""
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("phase demand file must contain a JSON array")

    demands: dict[PhaseKey, PhaseDemandSettings] = {}
    required = {
        "traffic_light_id",
        "program_id",
        "phase_index",
        "flow_veh_per_hour",
    }
    allowed = required | {"saturation_flow_veh_per_hour", "minimum_green_s"}
    for row in data:
        if not isinstance(row, dict):
            raise ValueError("each phase demand record must be a JSON object")
        if not required <= row.keys() or not row.keys() <= allowed:
            raise ValueError(
                "each record must include traffic_light_id, program_id, "
                "phase_index, and flow_veh_per_hour; only saturation_flow_veh_per_hour "
                "and minimum_green_s are optional"
            )
        traffic_light_id = row["traffic_light_id"]
        program_id = row["program_id"]
        phase_index = row["phase_index"]
        if not isinstance(traffic_light_id, str) or not traffic_light_id:
            raise ValueError("traffic_light_id must be a non-empty string")
        if not isinstance(program_id, str) or not program_id:
            raise ValueError("program_id must be a non-empty string")
        if isinstance(phase_index, bool) or not isinstance(phase_index, int) or phase_index < 0:
            raise ValueError("phase_index must be a non-negative integer")

        key = (traffic_light_id, program_id, phase_index)
        if key in demands:
            raise ValueError(f"duplicate phase demand record for {key}")
        values = (
            row["flow_veh_per_hour"],
            row.get("saturation_flow_veh_per_hour", 1800.0),
            row.get("minimum_green_s", 5.0),
        )
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
            raise ValueError(f"numeric demand values required for {key}")
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"numeric demand values must be finite for {key}")
        flow_veh_per_hour = float(values[0])
        if seed is not None:
            rng = random.Random(f"{seed}:{traffic_light_id}:{program_id}:{phase_index}")
            flow_veh_per_hour *= 0.9 + 0.2 * rng.random()
        demands[key] = PhaseDemandSettings(
            flow_veh_per_hour=flow_veh_per_hour,
            saturation_flow_veh_per_hour=float(values[1]),
            minimum_green_s=float(values[2]),
        )
    return demands


def required_phase_keys(network_file: Path) -> tuple[PhaseKey, ...]:
    """Return all green-phase keys that must be present in a demand file."""
    return _required_phase_keys(_read_network(network_file))


def _required_phase_keys(network: Any) -> tuple[PhaseKey, ...]:
    keys: list[PhaseKey] = []
    for traffic_light in network.getTrafficLights():
        traffic_light_id = traffic_light.getID()
        for program_id, program in traffic_light.getPrograms().items():
            if program.getType() != "static":
                raise ValueError(
                    f"traffic light {traffic_light_id} program {program_id} "
                    "is not static; refusing to rewrite it"
                )
            phases = program.getPhases()
            keys.extend(
                (traffic_light_id, program_id, index)
                for index, phase in enumerate(phases)
                if _has_green(phase.state)
            )
    if not keys:
        raise ValueError("network has no static green traffic-light phases")
    return tuple(keys)


def build_fixed_time_additional(
    network_file: Path,
    phase_demands: dict[PhaseKey, PhaseDemandSettings],
    *,
    min_cycle_s: float = 30.0,
    max_cycle_s: float = 120.0,
    program_prefix: str = "webster",
) -> ET.Element:
    """Build SUMO additional-file traffic-light programs without editing the network."""
    if not program_prefix.strip():
        raise ValueError("program_prefix must not be empty")
    network = _read_network(network_file)
    required_keys = set(_required_phase_keys(network))
    supplied_keys = set(phase_demands)
    missing = required_keys - supplied_keys
    extra = supplied_keys - required_keys
    if missing or extra:
        raise ValueError(
            f"phase demand keys mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )

    root = ET.Element("additional")
    for traffic_light in network.getTrafficLights():
        traffic_light_id = traffic_light.getID()
        for program_id, program in traffic_light.getPrograms().items():
            phases = program.getPhases()
            green_indexes = [
                index for index, phase in enumerate(phases) if _has_green(phase.state)
            ]
            if not green_indexes:
                generated_program = ET.SubElement(
                    root,
                    "tlLogic",
                    {
                        "id": traffic_light_id,
                        "programID": f"{program_prefix}_{program_id}",
                        "offset": str(program.getOffset()),
                        "type": "static",
                    },
                )
                _copy_phases(generated_program, phases, {})
                continue

            clearance_by_green = _clearance_by_green(phases, green_indexes)
            phase_flows = [
                PhaseFlow(
                    phase_id=index,
                    flow_veh_per_hour=phase_demands[
                        (traffic_light_id, program_id, index)
                    ].flow_veh_per_hour,
                    saturation_flow_veh_per_hour=phase_demands[
                        (traffic_light_id, program_id, index)
                    ].saturation_flow_veh_per_hour,
                    minimum_green_s=phase_demands[
                        (traffic_light_id, program_id, index)
                    ].minimum_green_s,
                    clearance_s=clearance_by_green[index],
                )
                for index in green_indexes
            ]
            plan = calculate_webster_plan(
                phase_flows,
                min_cycle_s=min_cycle_s,
                max_cycle_s=max_cycle_s,
            )
            green_durations = {
                split.phase_id: split.green_s for split in plan.green_splits
            }
            generated_program = ET.SubElement(
                root,
                "tlLogic",
                {
                    "id": traffic_light_id,
                    "programID": f"{program_prefix}_{program_id}",
                    "offset": _format_seconds(
                        float(program.getOffset()) % plan.cycle_length_s
                    ),
                    "type": "static",
                },
            )
            _copy_phases(generated_program, phases, green_durations)
    return root


def write_fixed_time_additional(
    network_file: Path,
    demand_file: Path,
    output_file: Path,
    *,
    min_cycle_s: float = 30.0,
    max_cycle_s: float = 120.0,
    program_prefix: str = "webster",
    seed: int | None = None,
) -> None:
    if network_file.resolve() == output_file.resolve():
        raise ValueError("output file must not overwrite the source network")
    root = build_fixed_time_additional(
        network_file,
        load_phase_demands(demand_file, seed=seed),
        min_cycle_s=min_cycle_s,
        max_cycle_s=max_cycle_s,
        program_prefix=program_prefix,
    )
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(output_file, encoding="utf-8", xml_declaration=True)


def _read_network(network_file: Path) -> Any:
    if not network_file.is_file():
        raise FileNotFoundError(f"SUMO network does not exist: {network_file}")
    return sumolib.net.readNet(str(network_file), withPrograms=True)


def _has_green(state: str) -> bool:
    has_green = "G" in state or "g" in state
    has_yellow = "y" in state or "Y" in state
    return has_green and not has_yellow


def _copy_phases(
    generated_program: ET.Element,
    phases: list[Any],
    green_durations: dict[int, float],
) -> None:
    for index, phase in enumerate(phases):
        original_duration = _phase_duration(phase, index)
        duration = green_durations.get(index, original_duration)
        attributes = {
            "duration": _format_seconds(duration),
            "state": phase.state,
        }
        if phase.name:
            attributes["name"] = phase.name
        ET.SubElement(generated_program, "phase", attributes)


def _clearance_by_green(phases: list[Any], green_indexes: list[int]) -> dict[int, float]:
    green_set = set(green_indexes)
    clearances: dict[int, float] = {}
    for position, green_index in enumerate(green_indexes):
        next_green_index = green_indexes[(position + 1) % len(green_indexes)]
        phase_index = (green_index + 1) % len(phases)
        clearance_s = 0.0
        while phase_index != next_green_index:
            if phase_index not in green_set:
                clearance_s += _phase_duration(phases[phase_index], phase_index)
            phase_index = (phase_index + 1) % len(phases)
        clearances[green_index] = clearance_s
    return clearances


def _phase_duration(phase: Any, index: int) -> float:
    duration = phase.duration
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(duration)
        or duration <= 0
    ):
        raise ValueError(f"SUMO phase {index} must have a finite positive duration")
    return float(duration)


def _format_seconds(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def load_seed(config_file: Path | None, cli_seed: int | None) -> int | None:
    if cli_seed is not None:
        if isinstance(cli_seed, bool):
            raise ValueError("seed must be an integer")
        return cli_seed
    if config_file is None:
        return None
    if not config_file.is_file():
        raise FileNotFoundError(f"configuration does not exist: {config_file}")
    data = json.loads(config_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("configuration must be a JSON object")
    seed = data.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer")
    return seed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Webster-timed SUMO traffic-light programs."
    )
    parser.add_argument("network", type=Path, help="source .net.xml file")
    parser.add_argument("demands", type=Path, help="JSON array of phase demand records")
    parser.add_argument("output", type=Path, help="destination SUMO additional XML file")
    parser.add_argument("--min-cycle", type=float, default=30.0)
    parser.add_argument("--max-cycle", type=float, default=120.0)
    parser.add_argument("--program-prefix", default="webster")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "backend" / "agent_config.json",
    )
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    seed = load_seed(args.config, args.seed)
    write_fixed_time_additional(
        args.network,
        args.demands,
        args.output,
        min_cycle_s=args.min_cycle,
        max_cycle_s=args.max_cycle,
        program_prefix=args.program_prefix,
        seed=seed,
    )


if __name__ == "__main__":
    main()
