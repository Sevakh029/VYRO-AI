# Repository Audit

Audit date: 2026-11-24

## Initial audit snapshot

The findings in this section record the repository before the implementation
work below. They are historical, not the current status.

### Controller

| Item | Finding |
|---|---|
| controller/ tree | PRESENT; P2 sources, tests, reading notes, and sandbox scripts exist. |
| controller/src/vyro_controller/webster.py | PRESENT and implemented with bounded Webster cycle and green-split logic. |
| controller/src/vyro_controller/state.py | PRESENT; SystemState and Action are transport-independent UTC-aware dataclasses. |
| controller/src/vyro_controller/seeds.py | PRESENT; tuning seeds 1-5 and test seeds 100-109 are disjoint. |
| controller/docs/state_spec.md | PRESENT. |
| Fixed-time plan generator | PRESENT as simulation/generate_fixed_time_plan.py, but the repository plan calls for sim/ and net phase data is outside the controller. |

### Backend

| Item | Finding |
|---|---|
| backend/ tree | PRESENT with FastAPI, MQTT, schemas, WebSocket, SQLite, and fake vehicle code. |
| backend /health | PRESENT in backend/src/vyro_backend/app.py. |
| Latest MQTT message store | PRESENT in MQTTSubscriber.LatestMessageStore. |
| Pydantic schemas | PRESENT for vehicle state, intersection state, signal command, vehicle advisory, metrics snapshot, preemption request, and controller ack. |
| Example JSON | PRESENT for all currently modeled message types in schemas/examples/. |
| Schema UTC validation | PRESENT for datetime fields; naive/non-UTC datetimes are rejected in model validation. |
| fake_vehicle_generator | PRESENT and publishes VehicleState messages. |
| WebSocket broadcast | PRESENT at /ws through WebSocketManager. |
| SQLite logger | PRESENT; stores topic, payload, UTC received time, and schema version. It is not yet complete about a valid/error schema. |
| hello_mqtt | PRESENT. |
| mqtt_subscriber | PRESENT. |
| backend/Dockerfile | PRESENT. |

### Broker and infrastructure

| Item | Finding |
|---|---|
| mosquitto/config/mosquitto.conf | PRESENT; allow_anonymous false and password_file are configured. |
| Mosquitto credentials | BROKEN for the plan: compose uses hardcoded fallback credentials and rewrites the password file with an inline command. |
| Compose port binding | BROKEN for the plan: ports are not restricted to localhost. |
| Mosquitto healthcheck | MISSING. |
| .github/workflows | PRESENT; only a Python 3.11 test job exists. |

### Simulation

| Item | Finding |
|---|---|
| sim/ directory | PRESENT but currently contains only area_report.md. |
| simulation/ directory | PRESENT with fixed-time plan, Traci bridge, OSM exports, and tests. |
| sim/ netreader/adapter area | PARTIAL: fixed-time logic is in simulation/, while plan ownership requires sim/net_reader.py and plain dataclasses. |
| Yerevan net file | MISSING as yerevan_v0.net.xml. |
| Candidate OSM exports | PRESENT under simulation/osm/yerevan/ for three candidate areas. |

### Dashboard

| Item | Finding |
|---|---|
| dashboard/ tree | PRESENT as a Vite React app. |
| Root package layout | PARTIAL/BROKEN: package.json and package-lock.json remain at repository root and dashboard lacks full React/Leaflet/TypeScript setup. |
| Yerevan map | PRESENT; only react/leaflet packages are not wired into source as a complete typed dashboard. |
| WebSocket typed reconnect hook | MISSING. |

### Schemas and records

| Item | Finding |
|---|---|
| Schemas single-source examples | PARTIAL: example JSON exists, but some models use different version values (v1.0/v1.1) and no phase 4 v0.2 migration is complete. |
| docs/ architecture records | PRESENT for prompt-log, security, and topics. |
| docs/audit.md | CREATED by this audit. |

### Other planned folders

| Item | Finding |
|---|---|
| agents/ | MISSING |
| experiments/ | MISSING |

## Recheck correction (2026-11-24)

The findings above are the initial baseline, not current status. SUMO 1.28.0 is
installed; all three Yerevan candidate networks exist, and the bundled headless
TraCI example completed 100 steps. Simulation sources and tests have moved to
`sim/`. The dashboard lockfile is regenerated, and clean install, production
build, and frontend tests pass.

Docker Desktop is installed and its Linux engine now runs. The backend image
builds, and Compose starts both services healthy. A container-level check
confirmed MQTT credentials are required, valid vehicle messages reach backend
state and SQLite, and invalid broker credentials are rejected. That runtime
check exposed a root-owned Mosquitto password file that the broker could not
read after dropping privileges; the entrypoint now assigns it to the
`mosquitto` user.

The selected OSM area has been reconverted as `sim/net/yerevan_v0.net.xml`;
SUMO reports 9 signal controllers. `netcheck.py` reports 399/516 edges in the
largest connected component (77.3%) and 90.3% when ignoring lane connections.
The disconnected fringe roads and clipped turn restrictions remain known OSM
limitations; no speculative lane connections or signal timings were added.
The network's synthetic smoke-demand route set was validated and all 60
generated vehicles completed a SUMO run. This verifies plumbing only, not a
traffic study.

The dashboard now loads road and signal geometry exported from that network,
and the TraCI bridge waits for MQTT connection before advancing SUMO. The live
SUMO-to-MQTT-to-backend-to-dashboard run exposed a missing optional Uvicorn
WebSocket dependency; it is now an explicit backend dependency, and the Compose
health check verifies both `/health` and a real `/ws` handshake. All 60
synthetic vehicles reached backend state and SQLite. The dashboard displayed
live vehicles and speed, then cleared stale states after the 15-second expiry.

The Python suite (142 tests), Ruff, dashboard build/tests, Compose validation,
Docker image build, WebSocket health check, and broker/backend integration
checks pass. No measured Yerevan demand or calibrated experiment was run.
Synthetic random trips are used only for the reproducible software smoke test.

| Repository area | Current status |
|---|---|
| mosquitto/ | PRESENT |
| docs/ | PRESENT |
| schemas/ | PRESENT |
| dashboard/ | PRESENT |
| controller/ | PRESENT |
| backend/ | PRESENT |
