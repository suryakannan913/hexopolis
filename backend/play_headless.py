"""Headless Hexopolis — play a complete 1v1 Catan game through the engine.

No UI, no web server: this drives app.engine directly, renders the board as
text, plays a full self-play game to a real 15-VP win, and then proves
reproducibility by replaying the same seed.

Usage (from backend/):
    python3 play_headless.py [seed]
"""
import random
import sys

from app.engine import (
    CITY,
    WINNING_POINTS,
    Phase,
    apply_action,
    legal_actions,
    new_game,
)
from app.engine.policy import choose_action
from app.models.board import Resource

CELL = 9
ROW_ORDER = [-2, -1, 0, 1, 2]  # axial r, top to bottom
ICON = {Resource.WOOD: "wood", Resource.WHEAT: "wheat", Resource.ORE: "ore",
        Resource.BRICK: "brick", Resource.SHEEP: "sheep", None: "desert"}


def render_board(state) -> str:
    rows = {}
    for h in state.board.hexes.values():
        rows.setdefault(h.coord.r, []).append(h)
    for r in rows:
        rows[r].sort(key=lambda h: h.coord.q + h.coord.r / 2)
    width = max(len(v) for v in rows.values())
    lines = []
    for r in ROW_ORDER:
        row = rows.get(r, [])
        indent = " " * ((width - len(row)) * CELL // 2)
        res_line, num_line = [], []
        for h in row:
            robber = " R" if h.coord == state.robber else ""
            res_line.append((ICON[h.resource] + robber).center(CELL))
            num = "--" if h.dice_number is None else str(h.dice_number)
            num_line.append(f"({num})".center(CELL))
        lines += [indent + "".join(res_line), indent + "".join(num_line), ""]
    return "\n".join(lines)


def summary(state) -> str:
    out = [f"phase={state.phase.value} turn={state.turn_number} "
           f"current=P{state.current_player} last_roll={state.last_roll}"]
    for p in state.players:
        res = " ".join(f"{r.value[:2]}:{p.resources[r]}" for r in Resource)
        builds = sum(1 for _, (o, k) in state.buildings.items() if o == p.id and k != CITY)
        cities = sum(1 for _, (o, k) in state.buildings.items() if o == p.id and k == CITY)
        out.append(
            f"  P{p.id} {p.name:<10} visibleVP={state.visible_vp(p.id):>2} "
            f"totalVP={state.total_vp(p.id):>2} | settle={builds} city={cities} "
            f"roads={15 - p.roads_left} knights={p.knights_played} | {res}"
        )
    out.append(f"  LongestRoad={state.longest_road_owner} LargestArmy={state.largest_army_owner} "
               f"bank={{{', '.join(f'{r.value[:2]}:{n}' for r, n in state.bank.items())}}}")
    return "\n".join(out)


def play(seed: int):
    state = new_game(("Blue", "Red"), seed=seed)
    rng = random.Random(seed)  # policy randomness, separate stream from the game's
    plies = 0
    while not state.is_terminal() and plies < 30_000:
        acts = legal_actions(state)
        apply_action(state, choose_action(state, acts, rng), validate=False)
        plies += 1
    return state, plies


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    print(f"=== New game (seed={seed}) ===")
    state = new_game(("Blue", "Red"), seed=seed)
    print(render_board(state))
    print(summary(state))

    print("\n=== Self-play to completion (heuristic policy, both seats) ===")
    state, plies = play(seed)
    print(render_board(state))
    print(summary(state))
    if state.winner is None:
        print(f"\nNo winner within {plies} plies — this should not happen; "
              f"win target is {WINNING_POINTS}.")
        sys.exit(1)
    w = state.players[state.winner]
    print(f"\n>>> {w.name} (P{w.id}) WINS with {state.total_vp(w.id)} VP "
          f"on turn {state.turn_number} ({plies} decisions).")

    # Reproducibility: the same seed must replay to the identical outcome.
    again, plies2 = play(seed)
    same = (again.winner, again.turn_number, plies2) == (state.winner, state.turn_number, plies)
    print(f">>> Reproducibility check (same seed, fresh game): "
          f"{'IDENTICAL' if same else 'MISMATCH'} "
          f"(winner={again.winner}, turns={again.turn_number}, decisions={plies2})")
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
