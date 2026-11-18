# VYRO Controller

This directory owns the pure-Python `vyro_controller` library. Its core API must not import
MQTT, FastAPI, SUMO, TraCI, file I/O, or simulator ground-truth data.

## Setup

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Phase status

- **Phase 0:** repository skeleton and test tooling.
- **Phase 1:** install SUMO first, then run `python controller\sandbox\hello_traci.py`.
- **Phase 2:** state and action API; to be added after Phase 1.
- **Phase 3:** Webster fixed-time plans and sandbox plan generation; to be added after Phase 2.

## Tests

```powershell
python -m pytest
python -m ruff check controller/src controller/tests
```

## Seeds

`TUNING_SEEDS` is reserved for algorithm calibration. `TEST_SEEDS` is reserved for tests and
must not be used for tuning. Test seeds are not active until explicitly requested.

