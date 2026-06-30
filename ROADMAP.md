# Hexopolis — Roadmap

Status: the core loop is real and playable end-to-end (opening placement → roll → collect → build → win), and the board has a Colonist-style canvas. This document tracks what's broken, what's missing, and how the UI evolves toward a polished Colonist.io-style client.

Priorities: **P0** = correctness bug or blocker, **P1** = core gameplay gap, **P2** = depth / polish.

---

## 1. Critical bugs to fix

### P0 — correctness
- [ ] **Bank trades enforce no ratio.** `GameService.execute_trade` only checks you own the resources you give — it never validates a 4:1 (or port) ratio, so a player can give 1 and receive any amount. Enforce `give == 4× received` for bank trades (and respect ports later).
- [ ] **The "desert" is a mislabeled resource hex.** The board has a hex with roll number 7 that still carries a resource (wheat) — it renders a resource icon, never produces (7 is skipped), and there's no real desert. Make it a true desert: no resource, no number, robber's start.
- [ ] **Board layout is identical every game.** Resources and number tokens are hard-coded in `Board._init_hexes`. Shuffle them per game (ideally with the standard number-token distribution) for replayability.

### P1 — rules gaps that affect fairness
- [ ] **Rolling a 7 silently voids production** with no robber. Implement the robber: on a 7, players over 7 cards discard half, the roller moves the robber to a hex, and steals a card from an adjacent opponent. At minimum, add the discard so a 7 isn't a no-op.
- [ ] **Win pacing is broken.** 10 points = 10 settlements, each costing 4 resources under the distance rule — practically unreachable. Add **city upgrades** (settlement → city = 2 points, double production) and/or tune the target so games finish.

---

## 2. Gameplay roadmap

| Priority | Feature | Notes |
|----------|---------|-------|
| P1 | **Bank trading (4:1) + trade UI** | Endpoint exists; needs ratio enforcement (above) and a UI. Biggest anti-stall fix. |
| P1 | **City upgrades** | Settlement → city: 2 points, 2× resources. Unblocks the win condition. |
| P1 | **Robber on 7** | Discard, move robber, steal. Core Catan tension. |
| P1 | **Board randomization** | Shuffle resources + number tokens each game. |
| P2 | **Smarter AI** | Currently greedy depth-1. Add light lookahead, smarter trading, and don't waste turns when stalled. |
| P2 | **Longest road / largest army** | +2 point bonuses; meaningful strategic layer. |
| P2 | **Ports / harbors (2:1, 3:1)** | The reference shows them on the coastline; wire them into trade ratios. |
| P2 | **Dev cards** | Knight / victory point / road building, etc. |

---

## 3. UI progression — toward a Colonist.io-style client

The reference (Colonist.io) layout: ocean + sand island board centered, a **right column** with event log + chat + bank counts, and a **bottom bar** with the player's resource cards, action buttons, dice, and avatar/score.

**Phase A — Board canvas ✅ (done)**
Ocean gradient, contiguous sand island, pointy-top hexes with perfect tiling, resource icons, probability number tokens, house-shaped settlements, outlined roads, glowing build spots.

**Phase B — Bottom HUD (next)**
- Resource **card row** (wood/brick/sheep/wheat/ore with live counts), like the reference's bottom-left hand.
- **Action button row**: trade, build road, build settlement, build city, end turn — with affordability states.
- **Dice visualization**: actual dice faces showing the last roll (bottom-center in the reference).
- Player **avatar + score + turn indicator** (bottom-right).

**Phase C — Right sidebar**
- **Event log**: "You placed a settlement", "AI rolled 🎲 8", "You received 🌲🌾" — the running feed in the reference. (Needs the backend to return per-action events, or the client to derive them from state diffs.)
- **Player panels**: each player's color, score, settlement/road/city counts, progress-to-win.
- **Bank counts**: remaining resource supply.

**Phase D — Interaction polish**
- Trade panel (modal or sidebar) for bank/port trades.
- Clear turn-phase guidance (roll → build → end), matching the reference's "Your Turn" banner + timer.
- Hover tooltips on hexes (resource + probability) and pieces.

**Phase E — Motion**
- Dice-roll animation, resource fly-in to the card row on production, settlement/city pop on placement, subtle piece shadows. (Foundations already exist in `animations.css`.)

**Phase F — Theming & extras**
- Harbors/ports drawn on the coastline (the little ships in the reference), robber piece on the board.
- Responsive / mobile layout, fullscreen toggle.

---

## 4. Infrastructure & deployment

- [ ] **Persistence** — games are in-memory (`games_db` dict); lost on restart. Move to Postgres (SQLAlchemy is already a dependency).
- [ ] **Deploy** — frontend to Vercel, backend to Render; wire `NEXT_PUBLIC_API_URL` + CORS to the deployed origin.
- [ ] **CI** — run `pytest` (105 tests) on push via GitHub Actions.
- [ ] **README screenshot** — drop a gameplay PNG at `docs/screenshot.png` (README already references it).
- [ ] **Multiplayer** (stretch) — human-vs-human over WebSockets.

---

## Suggested order of attack

1. **P0 bugs** (trade ratio, real desert, board randomization) — small, high-credibility fixes.
2. **Bottom HUD (Phase B)** + **bank trade UI** — biggest combined visual + functional jump.
3. **City upgrades + win tuning** — makes games actually finishable.
4. **Event log + sidebar (Phase C)** — the other half of the Colonist look.
5. **Robber, then AI depth** — gameplay richness.
6. **Deploy + CI + screenshot** — make it live and portfolio-ready.
