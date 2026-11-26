# SUMO simulation

P1 owns SUMO networks, analysis, TraCI, and map exports in `sim/`. The repository
contains three Yerevan candidate networks and their OSM extracts under
`sim/osm/yerevan/`. The selected Barekamutyun/Kievyan candidate has been
reconverted from its checked-in OSM extract as `sim/net/yerevan_v0.net.xml`.
This is a pilot network generated from OpenStreetMap, not a survey-grade or
calibrated model.

## Headless TraCI smoke test

```powershell
$env:SUMO_HOME = "C:\Program Files (x86)\SUMO"
python sim\hello_traci.py
```

The script uses SUMO's bundled `tools/game/cross` example, advances 100
one-second steps, and prints active vehicle positions. It does not use a
Yerevan network.

## Netconvert

This command was checked against installed SUMO 1.28.0 `netconvert --help`:

```powershell
New-Item -ItemType Directory -Force sim\net | Out-Null
netconvert --osm-files sim\osm\yerevan\barekamutyun_kievyan_bbox.osm.xml `
  --output-file sim\net\yerevan_v0.net.xml --tls.guess --geometry.remove
```

The output contains 516 edges and 9 signal controllers. `--geometry.remove`
reduces unnecessary geometry segmentation. Do not add `--junctions.join` for
this extract: a checked run merged nearby signalized junctions, reducing the
controller count from 9 to 3 and the largest connected component from 77.3% to
75.5%. The selected OSM extract also has clipped turn-restriction relations and
disconnected fringe roads. SUMO's `netcheck.py` reports 399/516 edges in its
largest connected component (77.3%); `--ignore-connections` reports 90.3%.
These are limitations of the extract, not issues that can safely be fixed by
inventing turns or deleting roads. Route generation below validates connectivity
for every generated smoke-test trip.

The guessed signal programs are synthetic: each has 81 seconds green, 4 yellow,
and 5 all-red. Each current controller protects two opposing straight-through
movements. These timings are for software smoke tests only, not observed
Yerevan signal plans.

## Candidate screening

Run `python sim\rank_nets.py` to recompute the structural summary and write
`sim\area_report.md` from the checked-in candidates. The metric counts connected
lane transitions and lanes with no outgoing transition; a terminal lane is a
review indicator, not automatically a network defect.

## Fixed-time plan

`generate_fixed_time_plan.py` reads static programs through sumolib and writes
a SUMO additional XML file without modifying the source network. Each pure
green phase requires demand data keyed by traffic-light ID, program ID, and
phase index. Yellow and all-red phases are copied unchanged; infeasible
minimum-green and clearance constraints fail explicitly.

The checked-in Webster plan for the canonical `sim/net/yerevan_v0.net.xml`
uses the synthetic placeholder demand records in
`sim/plans/yerevan_v0_webster_demands.json`. These are for exercising the
pipeline only; each signal uses 900 veh/h, not measured or calibrated traffic
flow. The generated plan uses 28 seconds green, 4 seconds yellow, and 5 seconds
all-red at each signal. Regenerate the plan with:

```powershell
python sim\generate_fixed_time_plan.py `
  sim\net\yerevan_v0.net.xml `
  sim\plans\yerevan_v0_webster_demands.json `
  sim\plans\yerevan_v0_webster.add.xml
```

Demand generation reads `seed` from `backend/agent_config.json` by default.
Pass `--seed <integer>` to override the config, or `--config path\to\config.json`
to choose another JSON config. The seed deterministically varies synthetic
demand values around their configured baseline.

Load the additional file in SUMO with:

```powershell
sumo --net-file sim\net\yerevan_v0.net.xml `
  --additional-files sim\plans\yerevan_v0_webster.add.xml `
  --end 40 --no-step-log true
```

The additional file adds a `webster_0` static program for every signal. Select
that program at runtime with TraCI's `trafficlight.setProgram(tls_id,
"webster_0")`; the network's original program remains unchanged.

SUMO/TraCI APIs are inspected from the installed distribution before use. The
`sim` Python extra includes sumolib, TraCI, and pyproj for geographic projection
conversion.

## TraCI to MQTT

The bridge publishes observed vehicle positions, speed, and heading to
`vyro/v1/vehicle/state`. It converts SUMO x/y coordinates through the network's
declared projection with `sumolib.Net.convertXY2LonLat`. That conversion applies
the network's `netOffset`, so pass TraCI's network-local x/y directly without
adjusting the offset again. It does not interpolate bounding boxes or expose
hidden simulator state.

```powershell
$env:SUMO_HOME = "C:\Program Files (x86)\SUMO"
python sim\sumo_mqtt_bridge.py `
  sim\osm\yerevan\barekamutyun_kievyan.net.xml `
  path\to\routes.rou.xml
```

The bridge subscribes to `vyro/v1/controller/command` and validates each
`intersection_id`/`phase_id` pair against `sim/signals.json` before calling
TraCI `setPhase`. Invalid or unknown signals publish an acknowledgement with
`applied=false` and never call TraCI. Use `--signals path\to\signals.json` to
override the default configuration.

  ### End-to-end synthetic smoke scenario

  The following produces deterministic, synthetic demand for integration testing.
  It is not a traffic estimate or an experiment result. SUMO's `--validate` option
  routes each trip and retries trips that cannot be connected through the OSM
  extract. SUMO may warn about rejected samples while it is retrying.

  ```powershell
  New-Item -ItemType Directory -Force sim\output | Out-Null
  Push-Location sim\output
  try {
  python "$env:SUMO_HOME\tools\randomTrips.py" `
    --net-file ..\net\yerevan_v0.net.xml `
    --route-file yerevan-smoke.rou.xml `
    --begin 0 --end 120 --period 2 --seed 23 --min-distance 50 --validate
  } finally {
    Pop-Location
  }
  ```

  With the broker and backend running via `docker compose up -d --build`, start
  the dashboard with `npm run dev` from `dashboard/`, then publish actual TraCI
  positions:

  ```powershell
  $env:SUMO_HOME = "C:\Program Files (x86)\SUMO"
  $env:MQTT_HOST = "127.0.0.1"
  $env:MQTT_PORT = "1883"
  $env:MQTT_USERNAME = "your-user"
  $env:MQTT_PASSWORD = "your-password"
  python sim\sumo_mqtt_bridge.py `
    sim\net\yerevan_v0.net.xml `
    sim\output\yerevan-smoke.rou.xml
  ```

  The bridge waits for a successful MQTT connection before starting SUMO; a
  broker connection failure is reported rather than silently dropping the first
  vehicle states. The route file and SUMO run outputs are ignored by Git.

  The dashboard's `yerevan_network.geojson` is exported from this same canonical
  network with:

  ```powershell
  python sim\export_geojson.py sim\net\yerevan_v0.net.xml `
    dashboard\public\yerevan_network.geojson
  ```

  It includes road geometries and the 9 signal locations. The source OSM data is
  © OpenStreetMap contributors (ODbL).

## Signal configuration export

Export the canonical network's signal phases and controlled approaches/lanes:

```powershell
python sim\export_signals.py sim\net\yerevan_v0.net.xml sim\signals.json
```
