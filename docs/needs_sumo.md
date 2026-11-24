# Real SUMO run requirements

A real SUMO/TraCI run was not executed because SUMO could not be verified as
installed and no generated `sim/net/yerevan_v0.net.xml` exists in this workspace.

The mock TraCI and fixed-time XML tests do not require SUMO.

Before a real run, verify installed package signatures using:

```bash
python -c "import sumolib, traci; print(sumolib.__file__); print(traci.__file__)"
```
