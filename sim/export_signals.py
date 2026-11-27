"""Export traffic-signal configuration from a SUMO network."""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _has_green(state: str) -> bool:
    return ("G" in state or "g" in state) and "y" not in state and "Y" not in state


def export_signals(network_file: Path, output_file: Path) -> list[dict[str, Any]]:
    if not network_file.is_file():
        raise FileNotFoundError(f"SUMO network does not exist: {network_file}")

    root = ET.parse(network_file).getroot()
    programs: dict[str, list[dict[str, Any]]] = {}
    valid_phase_indices: dict[str, list[int]] = {}

    for logic in root.findall("tlLogic"):
        signal_id = logic.get("id")
        if not signal_id:
            continue
        phases: list[dict[str, Any]] = []
        valid_indices: list[int] = []
        for index, phase_element in enumerate(logic.findall("phase")):
            state = phase_element.get("state", "")
            duration_text = phase_element.get("duration")
            duration = float(duration_text) if duration_text is not None else 0.0
            if not math.isfinite(duration) or duration < 0:
                raise ValueError(
                    f"SUMO phase {index} for signal {signal_id} must have "
                    "a finite non-negative duration"
                )
            phases.append({"index": index, "duration_s": duration, "state": state})
            if _has_green(state):
                valid_indices.append(index)
        if signal_id not in programs:
            programs[signal_id] = phases
            valid_phase_indices[signal_id] = valid_indices

    approaches: dict[str, list[str]] = {signal_id: [] for signal_id in programs}
    lanes: dict[str, list[str]] = {signal_id: [] for signal_id in programs}
    for connection in root.findall("connection"):
        signal_id = connection.get("tl")
        if not signal_id or signal_id not in programs:
            continue
        from_edge = connection.get("from")
        from_lane = connection.get("fromLane")
        if from_edge:
            if from_edge not in approaches[signal_id]:
                approaches[signal_id].append(from_edge)
        if from_edge and from_lane is not None:
            lane_id = f"{from_edge}_{from_lane}"
            if lane_id not in lanes[signal_id]:
                lanes[signal_id].append(lane_id)

    signals = [
        {
            "signal_id": signal_id,
            "phases": programs[signal_id],
            "valid_phase_indices": valid_phase_indices[signal_id],
            "approaches": sorted(approaches[signal_id]),
            "lanes": sorted(lanes[signal_id]),
        }
        for signal_id in sorted(programs)
    ]

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(signals, indent=2) + "\n", encoding="utf-8")
    return signals


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("network", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export_signals(args.network, args.output)


if __name__ == "__main__":
    main()
