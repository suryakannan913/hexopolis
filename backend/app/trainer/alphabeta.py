"""Tier 4: expectiminimax with alpha-beta pruning.

Port of catanatron's AlphaBetaPlayer (BOT_LOGIC_REFERENCE.md §3.7) — the
reference doc's pick for strongest 1v1 bot, because its core simplification
(one maximizing side vs one jointly-minimizing side) is EXACT with a single
opponent. Ported as-is: node value = probability-weighted expectation over
expand()'s outcome children; max/min chosen by WHOSE DECISION the simulated
state presents (consecutive same-actor decisions stay on the same side, per
the source); leaves scored by the tier-3 value function from the advisee's
perspective; ALPHABETA_DEFAULT_DEPTH = 2 and a wall-clock deadline
(MAX_SEARCH_TIME_SECS = 20) as the safety valve.

Documented deviations:
- Terminal leaves are scored explicitly (+/-TERMINAL) instead of through the
  value formula. The source's formula has no enemy-VP term, so a leaf where
  the OPPONENT has already won would score as merely mediocre and the search
  could walk into forced losses; we do not copy that blind spot.
- Fully deterministic: chance is enumerated exactly via expand() (the
  source's execute_spectrum), never sampled, so there is no seed parameter.
- The source's optional list_prunned_actions pre-filter is not ported (its
  robber shortcut is 1v1-exact but the filter is an optimization, not logic;
  the deadline covers runtime).

Scores are value-function units (near-lexicographic in VP) — NOT win
probabilities. Use the Monte Carlo tiers for probabilities.
"""
import time
from typing import Dict, List, Optional

from app.engine import legal_actions
from app.engine.state import GameState
from app.trainer.spectrum import expand
from app.trainer.value_function import DEFAULT_WEIGHTS, ScoredAction, value_fn

ALPHABETA_DEFAULT_DEPTH = 2   # catanatron ALPHABETA_DEFAULT_DEPTH
MAX_SEARCH_TIME_SECS = 20.0   # catanatron MAX_SEARCH_TIME_SECS
TERMINAL = 1e18               # dominates every value_fn score


def _alphabeta(state: GameState, depth: int, alpha: float, beta: float,
               deadline: float, advisee: int, weights: Dict[str, float]) -> float:
    if state.is_terminal():
        return TERMINAL if state.winner == advisee else -TERMINAL
    if depth == 0 or time.monotonic() >= deadline:
        return value_fn(state, advisee, weights)

    maximizing = state.actor() == advisee
    best = float("-inf") if maximizing else float("inf")
    for action in legal_actions(state):
        expected = sum(
            p * _alphabeta(child, depth - 1, alpha, beta, deadline, advisee, weights)
            for child, p in expand(state, action)
        )
        if maximizing:
            best = max(best, expected)
            alpha = max(alpha, best)
        else:
            best = min(best, expected)
            beta = min(beta, best)
        if alpha >= beta:
            break
    return best


def alphabeta_recommend(state: GameState, depth: int = ALPHABETA_DEFAULT_DEPTH,
                        time_limit: float = MAX_SEARCH_TIME_SECS,
                        weights: Dict[str, float] = DEFAULT_WEIGHTS) -> List[ScoredAction]:
    """Rank every legal action for state.actor() by its expectiminimax value.

    Deterministic for a given state — repeated calls agree exactly.
    """
    if state.is_terminal():
        raise ValueError("game is over — nothing to recommend")
    if depth < 1:
        raise ValueError("depth must be >= 1")
    advisee = state.actor()
    deadline = time.monotonic() + time_limit

    # Each root action gets fresh (-inf, inf) bounds: the source only needs the
    # argmax and prunes siblings, but a trainer ranking needs every root value.
    results = []
    for action in legal_actions(state):
        expected = sum(
            p * _alphabeta(child, depth - 1, float("-inf"), float("inf"),
                           deadline, advisee, weights)
            for child, p in expand(state, action)
        )
        results.append(ScoredAction(action, expected))

    results.sort(key=lambda r: r.score, reverse=True)
    return results
