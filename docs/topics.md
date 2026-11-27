# MQTT topics

All VYRO MQTT messages use JSON UTF-8 payloads in the `vyro/v1/#` namespace.
Publish and subscribe with QoS 1.

| Topic | Direction | Schema |
| --- | --- | --- |
| `vyro/v1/vehicle/state` | vehicle/bridge -> backend | `VehicleState` |
| `vyro/v1/intersection/state` | bridge -> backend | `IntersectionState` |
| `vyro/v1/controller/command` | backend -> bridge | `SignalCommand` |
| `vyro/v1/controller/ack` | bridge -> backend | `ControllerAck` |
| `vyro/v1/vehicle/advisory` | backend/agent -> vehicle/dashboard | `VehicleAdvisory` |
| `vyro/v1/preemption/request` | controller -> bridge | `PreemptionRequest` |
| `vyro/v1/metrics/snapshot` | backend -> dashboard | `MetricsSnapshot` |

Schemas use `schema_version`. v0.1 is the starting set and v0.2 changes are
additive, requiring Pydantic models, examples, controller adapters, dashboard
types, and tests to stay synchronized. Freeze to v1.0 only after v0.2 validation.

## Backend command and acknowledgement flow

The backend validates `SignalCommand` payloads and publishes them with QoS 1 on
`vyro/v1/controller/command`. It subscribes to `vyro/v1/controller/ack`, validates
`ControllerAck` payloads, and matches each ack to a pending command by
`command_id`. Applied, rejected, timeout, unmatched, and publication-failure
outcomes are recorded by the command bus. An unmatched or timed-out ack is never
treated as successful application.
