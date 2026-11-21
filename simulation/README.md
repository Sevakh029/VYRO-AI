# SUMO helpers

Run the TraCI position-printing example from the repository root:

```powershell
python simulation\hello_traci.py
```

It opens the bundled SUMO GUI traffic example, advances 100 one-second steps,
and prints each active vehicle's position. It requires `SUMO_HOME` to point to
the SUMO installation. The Yerevan networks under `simulation\osm\yerevan`
are road-only and do not include vehicle routes.
