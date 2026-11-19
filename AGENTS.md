# VYRO Repository Agent Guide

## Architecture

- `controller/` owns the pure-Python traffic-control library. It must not depend on MQTT,
  FastAPI, SUMO, TraCI, file I/O, or simulator ground-truth data.
- `backend/` owns FastAPI, MQTT ingestion, in-memory state, logging, and WebSocket APIs.
- `mosquitto/` owns broker configuration.
- `docs/` owns cross-team architecture and working records.
- P1 owns SUMO networks and TraCI integration.
- P2 owns schemas of estimator/controller behavior and pure control algorithms.
- P4 owns the React dashboard and network map.

## MQTT Topics

Day 1 placeholders; names must remain stable once frozen:

- `vyro/v1/vehicle/state`
- `vyro/v1/intersection/state`
- `vyro/v1/controller/command`
- `vyro/v1/controller/ack`

Use the `vyro/v1/#` namespace and JSON UTF-8 payloads.

## Conventions

- Python requires 3.11+.
- Schemas and public message shapes belong in Pydantic models in `backend/src/vyro_backend/`.
- All wall-clock experiment timestamps and state timestamps must be timezone-aware UTC.
- Tests use pytest. Controller tests must use the reserved seed constants.
- Keep one feature per branch and add the focused tests with it.
- Commits must not contain secrets, credentials, generated result files, or virtual environments.

## Never Do

- Never let the controller read SUMO ground truth or use hidden simulator state.
- Never mix tuning seeds with test seeds.
- Never report or commit experiment numbers without the source CSV.
- Never merge a changed schema without updating examples and all affected packages.
- Never weaken the minimum-green, yellow/all-red, or valid-phase safety constraints.
- Never call SUMO/TraCI APIs unless their behavior is checked against the installed or official API.
