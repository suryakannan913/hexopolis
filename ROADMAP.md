# Hexopolis — Roadmap

## Where things stand

The project is now a **1v1 Catan trainer**: a headless rules engine, a
recommendation stack, and a web UI that plays against a bot with move hints.

- **Engine** (`backend/app/engine/`) — single source of truth for the full 1v1
  ruleset in [CATAN_1V1_RULES.md](Catan_1v1_Rules.md): snake-draft setup,
  cities, dev cards, robber (friendly-robber rule, 9-card discard), maritime
  trade with ports, Longest Road / Largest Army, finite bank, 15-VP win.
  Seedable RNG; `legal_actions` / `apply_action` / `copy` interface.
- **Trainer** (`backend/app/trainer/`) — four tiers ported from the catanatron
  bot reference: instant value function, depth-2 expectiminimax, flat Monte
  Carlo, and UCB1 MCTS (the MC tiers return win probabilities). CLI
  (`recommend_cli.py`) and API (`GET /game/{id}/recommend`).
- **UI** (`frontend/`) — action-based client: renders the served state, acts
  by posting `legal_actions` indices, auto-plays the AI, and overlays trainer
  hints (auto value-tier hints + on-demand Monte Carlo analysis, gold
  highlight on the recommended placement).
- **Tests** — 129 backend tests, green.

## Next

- [ ] **Domestic (player↔player) trade** — engine action + simple AI accept
  logic (D1 in the rules doc; deliberately deferred).
- [ ] **Stronger AI opponent** — the server bot is a simple heuristic; wire it
  to the alpha-beta tier for a real challenge.
- [ ] **Trainer UX** — post-game review (re-analyze each of your moves),
  "blunder" flagging when your move ranks far below the recommendation.
- [ ] **Persistence** — games live in memory; move to a DB for restarts.
- [ ] **Deploy** — Vercel (frontend) + Render (backend), CI running pytest.
- [ ] **Board polish** — piece animations, mobile layout, screenshot for the
  README.
