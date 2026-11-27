"""Generate and run a reproducible 15-minute synthetic demand scenario."""

import argparse
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEMAND_DURATION_SECONDS = 900
DEMAND_PERIOD_SECONDS = 2.0
DRAIN_TIMEOUT_SECONDS = 900


def validate_completed_run(summary_file: Path, tripinfo_file: Path) -> tuple[int, float]:
    summary = ET.parse(summary_file).getroot()
    if not len(summary):
        raise RuntimeError("SUMO summary contains no simulation steps")
    final_step = summary[-1]
    loaded = int(final_step.attrib["loaded"])
    inserted = int(final_step.attrib["inserted"])
    running = int(final_step.attrib["running"])
    waiting = int(final_step.attrib["waiting"])
    ended = int(final_step.attrib["ended"])
    teleports = int(final_step.attrib["teleports"])
    collisions = int(final_step.attrib["collisions"])
    if inserted != loaded or running or waiting or ended != loaded:
        raise RuntimeError(
            "demand did not clear before the drain timeout: "
            f"loaded={loaded}, inserted={inserted}, running={running}, "
            f"waiting={waiting}, ended={ended}"
        )
    if teleports or collisions:
        raise RuntimeError(
            f"simulation had {teleports} teleports and {collisions} collisions"
        )

    tripinfos = ET.parse(tripinfo_file).getroot()
    if len(tripinfos) != loaded or any("arrival" not in trip.attrib for trip in tripinfos):
        raise RuntimeError("tripinfo output contains unfinished or missing trips")
    last_arrival = max(
        (float(trip.attrib["arrival"]) for trip in tripinfos),
        default=0.0,
    )
    return loaded, last_arrival


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True, help="reproducible demand seed")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "output",
    )
    args = parser.parse_args()

    sumo_home_value = os.getenv("SUMO_HOME")
    if not sumo_home_value:
        raise RuntimeError("SUMO_HOME is not set")
    sumo_home = Path(sumo_home_value)
    sumo_binary = sumo_home / "bin" / ("sumo.exe" if os.name == "nt" else "sumo")
    random_trips = sumo_home / "tools" / "randomTrips.py"
    network_file = Path(__file__).resolve().parent / "net" / "yerevan_v0.net.xml"
    for required_file in (sumo_binary, random_trips, network_file):
        if not required_file.is_file():
            raise FileNotFoundError(f"Required SUMO input does not exist: {required_file}")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"normal_seed{args.seed}"
    route_file = output_dir / f"{prefix}.rou.xml"
    error_log = output_dir / f"{prefix}.routing.log"
    summary_file = output_dir / f"{prefix}.summary.xml"
    tripinfo_file = output_dir / f"{prefix}.tripinfo.xml"

    subprocess.run(
        [
            sys.executable,
            str(random_trips),
            "--net-file",
            str(network_file),
            "--route-file",
            str(route_file),
            "--begin",
            "0",
            "--end",
            str(DEMAND_DURATION_SECONDS),
            "--period",
            str(DEMAND_PERIOD_SECONDS),
            "--seed",
            str(args.seed),
            "--min-distance",
            "50",
            "--validate",
            "--threads",
            "1",
            "--error-log",
            str(error_log),
        ],
        check=True,
        cwd=output_dir,
    )

    subprocess.run(
        [
            str(sumo_binary),
            "--net-file",
            str(network_file),
            "--route-files",
            str(route_file),
            "--seed",
            str(args.seed),
            "--end",
            str(DEMAND_DURATION_SECONDS + DRAIN_TIMEOUT_SECONDS),
            "--time-to-teleport",
            "-1",
            "--summary-output",
            str(summary_file),
            "--tripinfo-output",
            str(tripinfo_file),
            "--tripinfo-output.write-unfinished",
            "--no-step-log",
            "true",
            "--duration-log.statistics",
        ],
        check=True,
    )

    trip_count, final_time = validate_completed_run(summary_file, tripinfo_file)
    print(
        f"Completed seed {args.seed}: {trip_count} trips, "
        f"{DEMAND_DURATION_SECONDS}s demand, drained by {final_time:g}s; "
        "0 teleports and 0 collisions."
    )


if __name__ == "__main__":
    main()
