"""Trainer proof-of-life CLI: build a position, print ranked moves with win
probabilities.

Usage (from backend/):
    python3 recommend_cli.py --seed 42 --advance 30            # flat Monte Carlo
    python3 recommend_cli.py --seed 42 --advance 30 --mcts     # UCB1 tree search

--advance N plays N plies of heuristic self-play from a fresh seeded game to
reach a mid-game position; forced single-option states (e.g. the mandatory
roll) are then auto-stepped so the advised position has a real choice.
"""
import argparse
import random
import sys

from app.engine import Phase, apply_action, legal_actions, new_game
from app.engine.actions import Action, ActionType
from app.engine.policy import choose_action
from app.models.board import Resource
from app.trainer import mcts_recommend, recommend


def describe(action: Action) -> str:
    v = action.value
    if action.type in (ActionType.BUILD_SETTLEMENT, ActionType.BUILD_CITY):
        coords = "/".join(f"({h.q},{h.r})" for h in sorted(v.hex_coords, key=lambda h: (h.q, h.r)))
        return f"{action.type.value} @ {coords}"
    if action.type == ActionType.BUILD_ROAD:
        return f"build_road @ ({v.hex1.q},{v.hex1.r})-({v.hex2.q},{v.hex2.r})"
    if action.type == ActionType.MOVE_ROBBER:
        return f"move_robber -> ({v.q},{v.r})"
    if action.type == ActionType.MARITIME_TRADE:
        give, recv = v
        return f"trade {give.value} -> {recv.value}"
    if action.type == ActionType.PLAY_YEAR_OF_PLENTY:
        return f"year_of_plenty: {', '.join(r.value for r in v)}"
    if action.type in (ActionType.PLAY_MONOPOLY, ActionType.DISCARD):
        return f"{action.type.value}: {v.value}"
    return action.type.value


def build_position(seed: int, advance: int):
    """Fresh seeded game advanced by heuristic self-play, stopped at a state
    where the actor has a genuine choice (forced moves are stepped through)."""
    state = new_game(("You", "Opponent"), seed=seed)
    rng = random.Random(seed)
    for _ in range(advance):
        if state.is_terminal():
            sys.exit(f"game ended during --advance (turn {state.turn_number}); "
                     f"use a smaller --advance or another seed")
        apply_action(state, choose_action(state, legal_actions(state), rng), validate=False)
    while not state.is_terminal() and len(legal_actions(state)) == 1:
        apply_action(state, legal_actions(state)[0], validate=False)
    if state.is_terminal():
        sys.exit("game ended while skipping forced moves; try another seed/--advance")
    return state


def main():
    ap = argparse.ArgumentParser(description="Rank legal moves by estimated win probability.")
    ap.add_argument("--seed", type=int, default=42, help="game + recommender seed")
    ap.add_argument("--advance", type=int, default=30, help="plies of heuristic self-play first")
    ap.add_argument("--sims", type=int, default=25, help="flat MC: simulations per action")
    ap.add_argument("--mcts", action="store_true", help="use UCB1 MCTS instead of flat MC")
    ap.add_argument("--mcts-sims", type=int, default=200, help="MCTS: total simulations")
    args = ap.parse_args()

    state = build_position(args.seed, args.advance)
    actor = state.actor()
    me = state.players[actor]
    n_actions = len(legal_actions(state))

    print(f"seed={args.seed} advance={args.advance} | phase={state.phase.value} "
          f"turn={state.turn_number} | advising P{actor} ({me.name})")
    print(f"VP: you {state.total_vp(actor)} vs opponent {state.total_vp(1 - actor)} | "
          f"hand: " + " ".join(f"{r.value[:2]}:{me.resources[r]}" for r in Resource))

    if args.mcts:
        print(f"\nMCTS: {args.mcts_sims} simulations over {n_actions} actions...")
        recs = mcts_recommend(state, num_simulations=args.mcts_sims, seed=args.seed)
    else:
        print(f"\nFlat Monte Carlo: {n_actions} actions x {args.sims} rollouts...")
        recs = recommend(state, sims_per_action=args.sims, seed=args.seed)

    print(f"\n{'#':>2}  {'win%':>6}  {'sims':>4}  action")
    for i, r in enumerate(recs, 1):
        bar = "#" * round(r.win_probability * 20)
        print(f"{i:>2}  {r.win_probability * 100:5.1f}%  {r.sims:>4}  "
              f"{describe(r.action):<44} {bar}")
    best = recs[0]
    print(f"\n>>> recommended: {describe(best.action)}  "
          f"(estimated win probability {best.win_probability * 100:.1f}%)")


if __name__ == "__main__":
    main()
