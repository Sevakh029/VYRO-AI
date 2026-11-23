# VYRO-AI

VYRO is a 12-week, simulation-based prototype for central traffic-state estimation and
adaptive traffic-signal control. The implementation is split into the role-owned areas
described in the project plan.

## P2: Central Controller

The pure-Python controller package lives in `controller/`.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
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
Vehicle state, intersection state, and controller command topics are supported;
`vyro/v1/controller/ack` remains rejected until the project defines its schema.
