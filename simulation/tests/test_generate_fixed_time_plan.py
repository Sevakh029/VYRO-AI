import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import sumolib

from simulation.generate_fixed_time_plan import (
    PhaseDemandSettings,
    build_fixed_time_additional,
    load_phase_demands,
    required_phase_keys,
    write_fixed_time_additional,
)

NETWORK_FILE = (
    Path(__file__).parents[1]
    / "osm"
    / "yerevan"
    / "barekamutyun_kievyan.net.xml"
)


def zero_flow_demands() -> dict[tuple[str, str, int], PhaseDemandSettings]:
    return {
        key: PhaseDemandSettings(flow_veh_per_hour=0)
        for key in required_phase_keys(NETWORK_FILE)
    }


def test_generates_additional_programs_from_sumolib_phases() -> None:
    root = build_fixed_time_additional(NETWORK_FILE, zero_flow_demands())
    generated = root.findall("tlLogic")
    source_net = sumolib.net.readNet(str(NETWORK_FILE), withPrograms=True)
    source_program_count = sum(
        len(traffic_light.getPrograms())
        for traffic_light in source_net.getTrafficLights()
    )

    assert len(generated) == source_program_count
    assert all(program.get("type") == "static" for program in generated)
    assert all(program.get("programID", "").startswith("webster_") for program in generated)
    assert all(program.findall("phase") for program in generated)


def test_zero_flow_plan_preserves_clearance_states_and_minimum_green() -> None:
    root = build_fixed_time_additional(NETWORK_FILE, zero_flow_demands())
    generated = root.find("tlLogic")
    assert generated is not None
    phases = generated.findall("phase")
    green_phases = [
        phase
        for phase in phases
        if "G" in phase.attrib["state"] or "g" in phase.attrib["state"]
    ]
    clearance_phases = [
        phase
        for phase in phases
        if "G" not in phase.attrib["state"] and "g" not in phase.attrib["state"]
    ]

    assert len(green_phases) == 1
    assert float(green_phases[0].attrib["duration"]) >= 5
    assert [phase.attrib["state"] for phase in clearance_phases] == ["yy", "rr"]
    assert [phase.attrib["duration"] for phase in clearance_phases] == ["4", "5"]


def test_rejects_missing_or_extra_phase_demands() -> None:
    demands = zero_flow_demands()
    missing_key = next(iter(demands))
    del demands[missing_key]

    with pytest.raises(ValueError, match="phase demand keys mismatch"):
        build_fixed_time_additional(NETWORK_FILE, demands)

    with pytest.raises(ValueError, match="phase demand keys mismatch"):
        build_fixed_time_additional(
            NETWORK_FILE,
            zero_flow_demands() | {("unknown", "0", 0): PhaseDemandSettings(0)},
        )


def test_loads_phase_demand_records_and_rejects_duplicates(tmp_path: Path) -> None:
    demand_file = tmp_path / "demands.json"
    demand_file.write_text(
        json.dumps(
            [
                {
                    "traffic_light_id": "tls-1",
                    "program_id": "0",
                    "phase_index": 1,
                    "flow_veh_per_hour": 250,
                }
            ]
        ),
        encoding="utf-8",
    )
    assert load_phase_demands(demand_file) == {
        ("tls-1", "0", 1): PhaseDemandSettings(flow_veh_per_hour=250)
    }

    demand_file.write_text(
        json.dumps(
            [
                {
                    "traffic_light_id": "tls-1",
                    "program_id": "0",
                    "phase_index": 1,
                    "flow_veh_per_hour": 250,
                },
                {
                    "traffic_light_id": "tls-1",
                    "program_id": "0",
                    "phase_index": 1,
                    "flow_veh_per_hour": 300,
                },
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_phase_demands(demand_file)


def test_writes_parseable_additional_xml(tmp_path: Path) -> None:
    demand_file = tmp_path / "demands.json"
    demand_file.write_text(
        json.dumps(
            [
                {
                    "traffic_light_id": traffic_light_id,
                    "program_id": program_id,
                    "phase_index": phase_index,
                    "flow_veh_per_hour": 0,
                }
                for traffic_light_id, program_id, phase_index in required_phase_keys(
                    NETWORK_FILE
                )
            ]
        ),
        encoding="utf-8",
    )
    output_file = tmp_path / "plans.add.xml"

    write_fixed_time_additional(NETWORK_FILE, demand_file, output_file)

    assert ET.parse(output_file).getroot().tag == "additional"
