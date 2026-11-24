import xml.etree.ElementTree as ET
from pathlib import Path

import sumolib

NETWORK = Path(__file__).parents[1] / "net" / "yerevan_v0.net.xml"


def test_canonical_network_meets_pilot_size_and_signal_safety_checks() -> None:
    network = sumolib.net.readNet(str(NETWORK), withPrograms=True)
    west, south, east, north = network.getBoundary()
    assert east - west <= 2000
    assert north - south <= 2000
    assert len(network.getTrafficLights()) == 9

    root = ET.parse(NETWORK).getroot()
    for traffic_light in network.getTrafficLights():
        connections = root.findall(f"connection[@tl='{traffic_light.getID()}']")
        direction_by_index = {
            int(connection.get("linkIndex", "-1")): connection.get("dir")
            for connection in connections
        }
        assert direction_by_index
        assert all(direction == "s" for direction in direction_by_index.values())

        for program in traffic_light.getPrograms().values():
            phases = program.getPhases()
            states = [phase.state for phase in phases]
            assert any("G" in state or "g" in state for state in states)
            assert any("y" in state or "Y" in state for state in states)
            assert any("r" in state or "R" in state for state in states)
            for state in states:
                green_links = [
                    direction_by_index[index]
                    for index, signal in enumerate(state)
                    if signal in "Gg"
                ]
                assert all(direction == "s" for direction in green_links)
