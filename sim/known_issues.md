# Known simulation issues

## Yerevan pilot network reachability

The canonical `sim/net/yerevan_v0.net.xml` is a pilot network generated from a
clipped OpenStreetMap extract, not a calibrated or fully connected traffic
model. Existing screening found 399/516 edges (77.3%) in the largest connected
component. `randomTrips.py --validate` may sample unreachable edge pairs and
emit routing warnings while retrying.

Observed with the seeded 15-minute normal-demand run (`--seed 23`, SUMO 1.28.0):

- Route generation emitted 87 warnings each for unreachable mandatory edges,
  missing connections, and invalid sampled routes. It still produced all 450
  requested trips after validation/retries.
- With teleporting disabled, all 450 vehicles inserted and arrived; there were
  0 teleports and 0 collisions. Demand ended at 900 seconds and the last
  vehicle arrived at 1145 seconds during the 900-second drain allowance.
- This verifies the selected seed and synthetic demand profile only. It does
  not establish real-world traffic volumes, network-wide connectivity, or
  deadlock-free behavior for every seed.
