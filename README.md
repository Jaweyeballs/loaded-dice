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

## CLI sandbox (local playtest)

```bash
pip install -e ".[dev]"
loaded-dice
# or: python -m loaded_dice.sandbox Alice Bob Carol
```

Type `help` in-game for commands. Default is 2 players with 1000 starting chips.

## Browser multiplayer (M3)

Players join from **different browsers** (or devices on the same LAN). Non-active
players can spectate the current turn and use the shop / view scoresheets.

Requires **Node.js** (for the Vite UI) and Python 3.9+.

**Terminal 1 — game server:**
```bash
pip install -e ".[web]"
loaded-dice-server
# or: uvicorn loaded_dice.server:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — web UI:**
```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173` in two windows (or two machines).

1. Host: enter a name → **Create room** → share the room code  
2. Guest: enter a name + code → **Join room**  
3. Host: **Start match** when 2+ players are seated  
4. Active player rolls / scores / casts; others spectate and can shop when allowed  

On another device on the same network, open `http://<host-lan-ip>:5173` (Vite)
and ensure the API is reachable (server bound with `--host 0.0.0.0`). You can
also set `VITE_API_BASE=http://<host-lan-ip>:8000` in `web/.env` if not using
the Vite proxy.

## Project layout

```
src/loaded_dice/   — core game engine + multiplayer server
web/               — React + Vite client
tests/             — unit tests
docs/GDD.md        — design document
```

## Roadmap

- [x] M0 — Core engine
- [x] M1 — Currency, shop, and consumables
- [x] M2 — Opponent-targeting effects
- [ ] M3 — Browser multiplayer (rooms + WebSockets — in progress)
- [ ] M4 — Deploy (Fly.io / Vercel) & playtest polish
- [ ] M5 — Broader playtest / balance
