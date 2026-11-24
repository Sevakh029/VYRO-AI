# SUMO run status

SUMO 1.28.0 is installed. The installed `traci.start` and
`traci.simulationStep` signatures and `sumolib.net.readNet` /
`Net.convertXY2LonLat` APIs were checked before use.

The bundled-cross example was run headlessly for 100 one-second steps using
`sim/hello_traci.py`. The selected Barekamutyun/Kievyan candidate was
reconverted from the checked-in OSM source to `sim/net/yerevan_v0.net.xml`.
The generated network has 9 signal controllers and loads in SUMO. Its signals
are guessed, and the OSM extract has disconnected roads and clipped turn
restrictions; see `sim/README.md`.

SUMO randomTrips produced 60 deterministic, route-validated synthetic vehicles,
and all 60 completed a headless pilot-network run. The same network, routes,
TraCI-to-MQTT bridge, Docker broker/backend, SQLite persistence, and invalid
credential rejection were smoke-tested. The live WebSocket dashboard received
vehicle states from this run; after 15 seconds without updates, the dashboard
removed the stale vehicles. A missing optional Uvicorn WebSocket dependency was
found during this check, added to the backend extra, and covered by the Compose
health check's `/ws` handshake. These checks are software integration evidence
only. No measured Yerevan demand, calibrated experiment, or claim about
real-world traffic performance is available.
