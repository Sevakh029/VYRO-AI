# SUMO helpers

Run the TraCI position-printing example from the repository root:

```powershell
python simulation\hello_traci.py
```

It opens the bundled SUMO GUI traffic example, advances 100 one-second steps,
and prints each active vehicle's position. It requires `SUMO_HOME` to point to
the SUMO installation. The Yerevan networks under `simulation\osm\yerevan`
are road-only and do not include vehicle routes.

## Webster fixed-time plans

`generate_fixed_time_plan.py` reads static signal programs using `sumolib`,
uses `vyro_controller` to calculate bounded Webster green splits, and writes
an additional XML file without modifying the source network. Every green phase
needs a demand record keyed by traffic-light ID, program ID, and phase index.
The JSON input is an array; optional saturation-flow and minimum-green values
default to 1,800 vehicles/hour and 5 seconds:

```json
[
  {
    "traffic_light_id": "11144080253",
    "program_id": "0",
    "phase_index": 0,
    "flow_veh_per_hour": 400
  }
]
```

The snippet is illustrative; provide one record for every green phase in the
network. Non-green clearance phases retain their original durations and states.
Oversaturated cycles use the configured maximum cycle; infeasible minimum-green
or clearance requirements fail explicitly.

```powershell
python simulation\generate_fixed_time_plan.py `
  simulation\osm\yerevan\barekamutyun_kievyan.net.xml `
  simulation\phase_demands.json `
  simulation\plans\barekamutyun_webster.add.xml
```

Load the generated file with the source network using SUMO's `--additional-files`
option. The controller package itself does not import SUMO or `sumolib`.
