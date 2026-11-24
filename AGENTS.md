# VYRO Repository Agent Guide

## Architecture

- `controller/` owns the pure-Python traffic-control library. It must not depend on MQTT,
  FastAPI, SUMO, TraCI, file I/O, or simulator ground-truth data.
- `backend/` owns FastAPI, MQTT ingestion, in-memory state, logging, and WebSocket APIs.
- `mosquitto/` owns broker configuration.
- `docs/` owns cross-team architecture and working records.
- `sim/` owns P1 SUMO network conversion, net analysis, TraCI and export tools.
- `schemas/` owns the shared example JSON payloads.
- `agents/` owns agent-specific operational configuration and .gitkeep placeholders.
- `experiments/` owns experiment metadata and source CSV references; result output is gitignored.
- `dashboard/` is P4-owned React/TypeScript dashboard code.
- `simulation/` is legacy P1 code and is being migrated to `sim/`; new P1 work belongs in `sim/`.
- P1 owns SUMO networks and TraCI integration.
- P2 owns schemas of estimator/controller behavior and pure control algorithms.
- P4 owns the React dashboard and network map.

## MQTT Topics

Frozen topics in the vyro/v1 namespace:

- `vyro/v1/vehicle/state`
- `vyro/v1/intersection/state`
- `vyro/v1/controller/command`
- `vyro/v1/controller/ack`
- `vyro/v1/vehicle/advisory`
- `vyro/v1/metrics/snapshot`

Schemas use a `schema_version` field. v0.1 is the starting schema set.
The v0.2 change set is applied in the Phase 4 PR and must be additive.
Every change updates Pydantic models, examples, adapters, dashboard types, and tests.
Freeze to v1.0 only after v0.2 validation is complete; it is not a current freeze.
Backend Pydantic models are authoritative. P2 proposes schema changes by PR.

Use the `vyro/v1/#` namespace and JSON UTF-8 payloads.

## Conventions

- Python requires 3.11+.
- Schemas and public message shapes belong in Pydantic models in `backend/src/vyro_backend/`.
- All wall-clock experiment timestamps and state timestamps must be timezone-aware UTC.
- Tests use pytest. Controller tests must use the reserved seed constants.
- Reserved seeds live in `controller/src/vyro_controller/seeds.py`: `TUNING_SEEDS` is
  `(1, 2, 3, 4, 5)` and `TEST_SEEDS` is `tuple(range(100, 110))`. They must remain disjoint.
- Keep one feature per branch and add the focused tests with it.
- Commits must not contain secrets, credentials, generated result files, or virtual environments.

## Never Do

- Never let the controller read SUMO ground truth or use hidden simulator state.
- Never mix tuning seeds with test seeds.
- Never report or commit experiment numbers without the source CSV.
- Never merge a changed schema without updating examples and all affected packages.
- Never weaken the minimum-green, yellow/all-red, or valid-phase safety constraints.
- Never call SUMO/TraCI APIs unless their behavior is checked against the installed or official API.
