# Simulation area

P1 owns SUMO inputs and TraCI integration in this folder.
The repository does not include a generated `yerevan_v0.net.xml`.
Recommended netconvert command:

```bash
netconvert --osm-files sim/osm/yerevan/yerevan.osm.xml \
  --output-file sim/net/yerevan_v0.net.xml \
  --tls.guess true --junctions.join true
```

Run without SUMO by exercising mock/phase parsing tests. Real TraCI runs require a
SUMO installation and a generated network.
