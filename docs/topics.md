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
