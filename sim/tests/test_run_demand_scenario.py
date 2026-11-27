import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from sim.run_demand_scenario import validate_completed_run


def _write_summary(path: Path, **attributes: int) -> None:
    root = ET.Element("summary")
    ET.SubElement(root, "step", {key: str(value) for key, value in attributes.items()})
    ET.ElementTree(root).write(path)


def _write_tripinfo(path: Path, count: int, *, complete: bool = True) -> None:
    root = ET.Element("tripinfos")
    for trip_id in range(count):
        attributes = {"id": str(trip_id)}
        if complete:
            attributes["arrival"] = "12"
        ET.SubElement(root, "tripinfo", attributes)
    ET.ElementTree(root).write(path)


def test_validate_completed_run_accepts_drained_no_teleport_run(tmp_path: Path) -> None:
    summary_file = tmp_path / "summary.xml"
    tripinfo_file = tmp_path / "tripinfo.xml"
    _write_summary(
        summary_file,
        time=1117,
        loaded=2,
        inserted=2,
        running=0,
        waiting=0,
        ended=2,
        teleports=0,
        collisions=0,
    )
    _write_tripinfo(tripinfo_file, 2)

    assert validate_completed_run(summary_file, tripinfo_file) == (2, 12.0)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"running": 1, "ended": 1}, "did not clear"),
        ({"teleports": 1}, "teleports"),
        ({"collisions": 1}, "collisions"),
    ],
)
def test_validate_completed_run_rejects_deadlock_or_simulation_defects(
    tmp_path: Path,
    overrides: dict[str, int],
    message: str,
) -> None:
    summary_file = tmp_path / "summary.xml"
    tripinfo_file = tmp_path / "tripinfo.xml"
    attributes = {
        "time": 900,
        "loaded": 2,
        "inserted": 2,
        "running": 0,
        "waiting": 0,
        "ended": 2,
        "teleports": 0,
        "collisions": 0,
    }
    attributes.update(overrides)
    _write_summary(summary_file, **attributes)
    _write_tripinfo(tripinfo_file, 2)

    with pytest.raises(RuntimeError, match=message):
        validate_completed_run(summary_file, tripinfo_file)


def test_validate_completed_run_rejects_unfinished_tripinfo(tmp_path: Path) -> None:
    summary_file = tmp_path / "summary.xml"
    tripinfo_file = tmp_path / "tripinfo.xml"
    _write_summary(
        summary_file,
        time=900,
        loaded=1,
        inserted=1,
        running=0,
        waiting=0,
        ended=1,
        teleports=0,
        collisions=0,
    )
    _write_tripinfo(tripinfo_file, 1, complete=False)

    with pytest.raises(RuntimeError, match="unfinished"):
        validate_completed_run(summary_file, tripinfo_file)
