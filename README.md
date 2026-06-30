# Loaded Dice

A multiplayer dice game built on classic Yahtzee scoring, wrapped in a
run-based economy: earn chips, spend them on consumables between rounds,
and cast effects that boost you or hinder the table. Full design lives in
[`docs/GDD.md`](docs/GDD.md).

## Setup

Create a virtual environment (do this on each machine you work from — it's
not synced through git):

**Mac/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Then install the package and dev dependencies:
```bash
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Project layout

```
src/loaded_dice/   — core game engine
tests/              — unit tests
docs/GDD.md        — design document
```

## Roadmap

- [x] M0 — Core engine (in progress: dice mechanics done, scoring next)
- [ ] M1 — Currency, shop, and consumables
- [ ] M2 — Opponent-targeting effects
- [ ] M3 — Browser UI (single-player)
- [ ] M4 — Multiplayer sync
- [ ] M5 — Deploy & playtest
