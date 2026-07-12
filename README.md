# 🏝️ Hexopolis

A Catan-inspired strategy game built from scratch — a hexagonal board, resource economy, settlement/road building, and a heuristic AI opponent you can actually lose to. Full-stack: a typed **FastAPI** game engine and a **Next.js + Canvas** client.

> Portfolio project exploring game-state modeling, hex-grid geometry, and adversarial AI search.

<!-- Add a gameplay screenshot at docs/screenshot.png and it will render here -->
<!-- ![Hexopolis board](docs/screenshot.png) -->

---

## Features

- **Real hex-grid engine** — axial/cube coordinate math, 19-hex board, vertices (settlements) and edges (roads) derived geometrically.
- **Full turn loop** — opening placement, dice roll, resource distribution, building, and win detection (first to 10 points).
- **Rules that hold** — settlement distance rule, road/settlement connectivity, resource costs, and legal-move validation enforced server-side.
- **Heuristic AI opponent** — evaluates board state and generates/scores legal moves (settlements, roads, bank trades), expanding its network turn over turn.
- **Interactive Canvas board** — click-to-place with corner/edge snapping, hover previews, resource icons, and probability-weighted number tokens.
- **105 backend tests** across board geometry, game logic, the service layer, the AI, and the API.

## Tech stack

| Layer | Tools |
|-------|-------|
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, pytest |
| Frontend | TypeScript, Next.js 15, React 19, Zustand, Tailwind CSS v4, HTML5 Canvas |

## Architecture

```
backend/
  app/
    models/      # HexCoord, Board, Vertex, Edge, Game, Player — core domain + geometry
    services/    # GameService — placement, dice, resource distribution, turn flow, validation
    ai/          # AIEvaluator + AIPlayer — state scoring and greedy move selection
    routes/      # FastAPI endpoints (create game, roll, build, trade, end turn, AI turn)
    schemas/     # Pydantic request/response models (board + game state serialization)
  tests/         # 105 tests: board, game, service, AI, API
  main.py        # app entry + CORS

frontend/
  app/           # Next.js routes: home (create game) + /game/[id]
  components/     # GameBoard (Canvas), ActionPanel, ResourcePanel, BuildPanel, Toast
  lib/           # hexUtils (hex↔pixel math, drawing), api client
  store/         # Zustand game-state store
  hooks/         # useGameState — fetch + poll game state
```

The board is generated and validated entirely on the backend and serialized over the API; the frontend renders that state and sends player actions back — no game rules live in the client.

## Getting started

**Prerequisites:** Python 3.9+, Node 18+.

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API runs at `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

App runs at `http://localhost:3000`.

### Tests

```bash
cd backend && pytest
```

## How to play

1. Enter your name and start a game vs. the AI.
2. **Opening placement:** click two corners to place your starting settlements (they grant your starting resources).
3. On your turn: **roll the dice** to collect resources from hexes adjacent to your settlements.
4. Spend resources to build **roads** (wood + brick) and **settlements** (wood + brick + wheat + sheep). Settlements must connect to your road network and can't sit next to another settlement.
5. First to **10 points** wins.

## Deployment

CI (GitHub Actions) runs `pytest` and the frontend typecheck/build on every push.

- **Backend → Render**: [render.yaml](render.yaml) blueprint — uvicorn app with a
  persistent disk for the SQLite event store (`HEXOPOLIS_DB`). Set
  `ALLOWED_ORIGINS` to the deployed frontend origin.
- **Frontend → Vercel**: import the repo, set the root directory to `frontend/`
  and `NEXT_PUBLIC_API_URL` to the Render URL.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the prioritized plan: known bugs, gameplay gaps (bank trading, robber on 7), and the UI direction toward a Colonist.io-style client.

---

Built with [Claude Code](https://claude.com/claude-code).
