"""Tier 1: flat Monte Carlo recommender.

Shape ported from catanatron's GreedyPlayoutsPlayer (BOT_LOGIC_REFERENCE.md
§3.10): for each legal action, apply it to a copy of the state and run N
independent rollouts to game end with the weighted-random policy, tallying how
often the advised player wins. Where the source bot argmaxes, we return the
full ranking — the win probability *is* the trainer's output.

Defaults ported as-is: 25 sims per action (DEFAULT_NUM_PLAYOUTS). Rollouts
that hit the ply cap count as losses, matching the source's TURNS_LIMIT
convention (winning_color() is None -> no win).

Chance handling: the engine resolves randomness (dice, dev draws, steals)
inside apply_action via state.rng, and GameState.copy() deliberately preserves
the RNG stream. Each simulation therefore RESEEDS its copy's rng from a
recommender-owned seeded RNG *before* applying the candidate action — so
stochastic outcomes vary across simulations (sampled chance nodes) while
recommend(seed=k) remains fully reproducible.
"""
import random
from dataclasses import dataclass
from typing import List, Optional

from app.engine import apply_action, legal_actions
from app.engine.actions import Action
from app.engine.state import GameState
from app.trainer.rollout_policy import weighted_random_policy

SIMS_PER_ACTION = 25   # catanatron GreedyPlayoutsPlayer DEFAULT_NUM_PLAYOUTS
PLY_CAP = 5_000        # analog of catanatron's TURNS_LIMIT rollout guard


@dataclass(frozen=True)
class Recommendation:
    action: Action
    win_probability: float
    sims: int  # simulations behind this estimate


def rollout(state: GameState, rng: random.Random, ply_cap: int = PLY_CAP) -> Optional[int]:
    """Play `state` to the end with the weighted-random policy on both seats.
    Mutates `state` (callers pass a copy). Returns the winner, or None at cap."""
    plies = 0
    while not state.is_terminal() and plies < ply_cap:
        acts = legal_actions(state)
        apply_action(state, weighted_random_policy(state, acts, rng), validate=False)
        plies += 1
    return state.winner


def _simulate(state: GameState, action: Action, sim_seed: int, ply_cap: int) -> Optional[int]:
    """One simulation: copy, reseed (diverge the chance stream), apply, roll out."""
    sim = state.copy()
    rng = random.Random(sim_seed)
    sim.rng = rng  # candidate action itself may consume randomness (roll, steal, draw)
    apply_action(sim, action, validate=False)
    return rollout(sim, rng, ply_cap)


def recommend(state: GameState, sims_per_action: int = SIMS_PER_ACTION,
              seed: Optional[int] = None, ply_cap: int = PLY_CAP) -> List[Recommendation]:
    """Rank every legal action for state.actor() by estimated win probability."""
    if state.is_terminal():
        raise ValueError("game is over — nothing to recommend")
    advisee = state.actor()
    master = random.Random(seed)

    results = []
    for action in legal_actions(state):
        wins = sum(
            _simulate(state, action, master.randrange(2**63), ply_cap) == advisee
            for _ in range(sims_per_action)
        )
        results.append(Recommendation(action, wins / sims_per_action, sims_per_action))

    results.sort(key=lambda r: r.win_probability, reverse=True)
    return results
