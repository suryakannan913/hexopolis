"""Rollout policy: a port of catanatron's WeightedRandomPlayer.

Source: BOT_LOGIC_REFERENCE.md §3.4 — random choice over legal actions with
the action list "bloated" so that economic actions dominate whenever legal:

    BUILD_CITY: 10000, BUILD_SETTLEMENT: 1000, BUY_DEVELOPMENT_CARD: 100,
    everything else: 1.

We draw with rng.choices(weights=...) instead of literally duplicating list
entries — the same distribution, without building a 10k-element list. Forced
decisions (roll, discard, robber move) fall out naturally: when only weight-1
actions are legal the choice is uniform among them, exactly as in the source.

Used for BOTH seats during rollouts (catanatron's run_playout does the same),
so estimates carry no seat bias.
"""
import random
from typing import List

from app.engine.actions import Action, ActionType
from app.engine.state import GameState

WEIGHTS_BY_ACTION_TYPE = {
    ActionType.BUILD_CITY: 10_000,
    ActionType.BUILD_SETTLEMENT: 1_000,
    ActionType.BUY_DEV_CARD: 100,
}


def weighted_random_policy(state: GameState, actions: List[Action],
                           rng: random.Random) -> Action:
    """Pick one legal action, weighted by WEIGHTS_BY_ACTION_TYPE (default 1)."""
    weights = [WEIGHTS_BY_ACTION_TYPE.get(a.type, 1) for a in actions]
    return rng.choices(actions, weights=weights, k=1)[0]
