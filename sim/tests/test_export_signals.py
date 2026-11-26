import json
from pathlib import Path

from sim.export_signals import export_signals


def test_export_signals_from_canonical_network() -> None:
    network_file = Path("sim/net/yerevan_v0.net.xml")
    output_file = Path("sim/signals.json")

    result = export_signals(network_file, output_file)

    assert len(result) == 9
    assert all(set(signal) == {
        "signal_id",
        "phases",
        "valid_phase_indices",
        "approaches",
        "lanes",
    } for signal in result)
    assert all(signal["valid_phase_indices"] == [0] for signal in result)
    assert all(len(signal["phases"]) == 3 for signal in result)
    assert all(signal["approaches"] for signal in result)
    assert all(signal["lanes"] for signal in result)

    persisted = json.loads(output_file.read_text(encoding="utf-8"))
    assert persisted == result
