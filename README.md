# VYRO-AI
hgghgh
VYRO is a 12-week, simulation-based prototype for central traffic-state estimation and
adaptive traffic-signal control. The implementation is split into the role-owned areas
described in the project plan.

## P2: Central Controller

The pure-Python controller package lives in `controller/`.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest







python -m ruff check controller/src controller/tests
```

P2 reading and setup notes are in
[controller/docs/day-1-reading-notes.md](controller/docs/day-1-reading-notes.md).
