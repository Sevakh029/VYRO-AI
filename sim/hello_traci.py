import os
import sys
from pathlib import Path
from typing import Any


def _load_traci(sumo_home: Path) -> Any:
    sys.path.insert(0, str(sumo_home / "tools"))
    import traci

    return traci


SIMULATION_SECONDS = 100


def main() -> None:
    sumo_home_value = os.environ.get("SUMO_HOME")
    if not sumo_home_value:
        raise RuntimeError("SUMO_HOME is not set.")
    sumo_home = Path(sumo_home_value)
    traci = _load_traci(sumo_home)
    sumo_gui = sumo_home / "bin" / "sumo-gui.exe"
    example = sumo_home / "tools" / "game" / "cross"
    network = example / "cross.net.xml"
    routes = example / "cross.rou.xml"
    if not sumo_gui.is_file() or not network.is_file() or not routes.is_file():
        raise FileNotFoundError(f"SUMO GUI or bundled example files not found under {sumo_home}")

    traci.start(
        [
            str(sumo_gui),
            "--net-file",
            str(network),
            "--route-files",
            str(routes),
            "--step-length",
            "1",
            "--delay",
            "0",
            "--start",
            "--quit-on-end",
        ]
    )
    try:
        for _ in range(SIMULATION_SECONDS):
            traci.simulationStep()
            simulation_time = traci.simulation.getTime()
            vehicle_ids = traci.vehicle.getIDList()
            if not vehicle_ids:
                print(f"t={simulation_time:.0f}s no vehicles", flush=True)
                continue

            for vehicle_id in vehicle_ids:
                x, y = traci.vehicle.getPosition(vehicle_id)
                print(
                    f"t={simulation_time:.0f}s vehicle={vehicle_id} x={x:.2f} y={y:.2f}",
                    flush=True,
                )
    finally:
        traci.close()


if __name__ == "__main__":
    main()
