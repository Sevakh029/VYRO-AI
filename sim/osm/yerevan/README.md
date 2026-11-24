# Yerevan OSM candidate areas

These OpenStreetMap extracts were downloaded on 2026-11-20 and converted with
SUMO 1.28.0. Each bounding box is approximately 0.68 km east-west by 0.89 km
north-south. The `.net.xml` files contain the converted road networks; no
vehicle demand or routes are included.

| Candidate | Bounding box (west, south, east, north) |
| --- | --- |
| Kentron / Republic Square | `44.5070,40.1740,44.5150,40.1820` |
| Barekamutyun / Kievyan | `44.4880,40.2020,44.4960,40.2100` |
| Sasuntsi Davit / Tigran Mets | `44.5050,40.1500,44.5130,40.1580` |

These are screening candidates around major roads and transport nodes, not a
ranking based on measured traffic counts. OpenStreetMap does not provide
traffic-volume measurements. `netconvert` completed for all three maps, but
reported some incomplete turn restrictions and transit stops near extract
boundaries; review those before using the networks for calibrated experiments.

The generated SUMO network extents differ from the input bounding boxes. See
`sim/area_report.md` for current projected network dimensions and the
reproducible `sim/rank_nets.py` screening.

Data attribution: © OpenStreetMap contributors, licensed under the
[Open Database License (ODbL)](https://www.openstreetmap.org/copyright).
