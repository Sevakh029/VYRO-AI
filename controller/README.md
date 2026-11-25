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
- **Day 1 P2:** Python dependencies, Webster/max-pressure reading notes, and toy-flow tests.
- **Controller contract:** `SystemState` matches `IntersectionState`; `Action` matches
  `SignalCommand`. See [state_spec.md](docs/state_spec.md).
- **Decision stub:** `decide(state)` returns an action that holds the current phase;
  phase selection is not implemented yet.
- **Webster baseline:** `vyro_controller.webster` calculates bounded cycle lengths and
  minimum-green-constrained splits. The SUMO file adapter is in
  `sim/generate_fixed_time_plan.py`, outside the pure controller package.

## Tests

```powershell
python -m pytest
python -m ruff check controller/src controller/tests
```

## Seeds

`TUNING_SEEDS` is reserved for algorithm calibration. `TEST_SEEDS` is reserved for tests and
must not be used for tuning. Test seeds are not active until explicitly requested.

