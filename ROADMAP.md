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

## Done since

- [x] **Perf**: board-geometry memoization + structural GameState.copy()
  (13x cheaper copies; MC analysis 10s -> ~4s).
- [x] **Persistence**: event-sourced SQLite store (seed + action log); games
  survive restarts by deterministic replay.
- [x] **SVG board**: viewBox scaling, DOM hit-testing, piece pop animations,
  always-visible open spots, port boats.
- [x] **Difficulty tiers**: easy (heuristic) / medium (value fn) / hard
  (expectiminimax), all replay-safe.
- [x] **Placement heatmap** (trainer scores shade the legal spots) and
  **post-game review** (per-decision rank vs the trainer, BEST/OK/WEAK).
- [x] **CI**: GitHub Actions running pytest + frontend typecheck/build;
  Render/Vercel deploy configs.

## Next

- [ ] **Deploy for real** — connect the repo on Render + Vercel (configs are
  in place; needs account hookup).
- [ ] **Domestic (player↔player) trade** — engine action + AI accept logic
  (D1 in the rules doc; deliberately deferred).
- [ ] **Win-probability review** — review currently uses the instant value
  tier; add an opt-in MC pass for probability-based blunder margins.
- [ ] **Frontend tests** — vitest for gameLog diffing, one Playwright flow.
- [ ] **Mobile layout** + README screenshot.
