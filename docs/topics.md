# MQTT topics

All VYRO MQTT messages use JSON UTF-8 payloads in the `vyro/v1/#` namespace.
Publish and subscribe with QoS 1.

| Topic | Direction | Schema |
| --- | --- | --- |
| `vyro/v1/vehicle/state` | vehicle/bridge -> backend | `VehicleState` |
| `vyro/v1/intersection/state` | bridge -> backend | `IntersectionState` |
| `vyro/v1/controller/command` | backend -> bridge | `SignalCommand` |
| `vyro/v1/controller/ack` | bridge -> backend | reserved; schema to be added v1.1 |

All schemas are frozen at v1.0. Additive changes require updating examples,
Pydantic models, controller adapters, and affected dashboard types.
