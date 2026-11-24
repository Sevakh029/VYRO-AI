# VYRO-AI
VYRO is a 12-week, simulation-based prototype for central traffic-state estimation and
adaptive traffic-signal control. The implementation is split into the role-owned areas
described in the project plan.

## Installation

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,backend,sim]"
Copy-Item .env.example .env
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,backend,sim]"
cp .env.example .env
```

Set a non-placeholder `MQTT_USERNAME` and `MQTT_PASSWORD` in `.env`.
`pyproject.toml` is the source of truth for Python dependencies.

## P2: Central Controller

The pure-Python controller package lives in `controller/`.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,backend,sim]"
python -m pytest
python -m ruff check controller/src controller/tests
```

P2 reading and setup notes are in
[controller/docs/day-1-reading-notes.md](controller/docs/day-1-reading-notes.md).

## P3: Backend and communications

Start the MQTT broker:

```powershell
docker compose up -d --build
```

Run the backend API:

```powershell
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "backend/src"
python -m uvicorn vyro_backend.app:app --host 127.0.0.1 --port 8000
```

Check it at <http://127.0.0.1:8000/health>.

Run the MQTT hello-world pair in separate terminals:

```powershell
$env:PYTHONPATH = "backend/src"
python -m vyro_backend.mqtt_subscriber
python -m vyro_backend.hello_mqtt
```

Run the fake-vehicle publisher in another terminal. It publishes the 200 stable
vehicle IDs once per second to `vyro/v1/vehicle/state`; broker settings can be
overridden with `MQTT_HOST` and `MQTT_PORT`:

```powershell
$env:PYTHONPATH = "backend/src"
python -m vyro_backend.fake_vehicle_generator
```

The backend validates supported MQTT topics against their existing schemas and
broadcasts valid messages to WebSocket clients at `ws://127.0.0.1:8000/ws`.
Supported topics include vehicle/intersection state, signal commands and
`vyro/v1/controller/ack`. Advisory and metrics topics are
`vyro/v1/vehicle/advisory` and `vyro/v1/metrics/snapshot`.
Public schemas use `schema_version: "0.2"` for the current additive v0.2 set.

The SQLite message log is stored at `VYRO_SQLITE_DB_PATH`; Docker uses
`/app/data/vyro_messages.db`.

## Dashboard

```bash
cd dashboard
npm install
npm run dev
npm run build
npm test
```

The map is centered on Yerevan and uses `dashboard/public/sample-network.geojson`
until a real exported SUMO network is available.

## SUMO simulation

No real SUMO results are committed. See [sim/README.md](sim/README.md) and
[docs/needs_sumo.md](docs/needs_sumo.md) for setup and netconvert commands.
