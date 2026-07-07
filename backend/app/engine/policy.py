"""Tiny heuristic policy used by the /ai-turn endpoint and the headless demo.

The priority ordering is ported in spirit from catanatron's
WeightedRandomPlayer (BOT_LOGIC_REFERENCE.md §3.4): strongly prefer
cities > settlements > dev cards over filler actions, with forced/phase
actions handled naturally by whatever is legal. Not a trainer — just enough
play strength to finish games.
"""
import random
from typing import List

from app.engine.actions import Action, ActionType
from app.engine.state import GameState

_PRIORITY = {
    ActionType.ROLL: 0,                 # rolling is mandatory; get it done first
    ActionType.DISCARD: 0,
    ActionType.MOVE_ROBBER: 0,
    ActionType.BUILD_CITY: 1,
    ActionType.BUILD_SETTLEMENT: 2,
    ActionType.PLAY_ROAD_BUILDING: 3,
    ActionType.BUILD_ROAD: 4,
    ActionType.BUY_DEV_CARD: 5,
    ActionType.PLAY_KNIGHT: 6,
    ActionType.PLAY_YEAR_OF_PLENTY: 6,
    ActionType.PLAY_MONOPOLY: 6,
    ActionType.MARITIME_TRADE: 7,
    ActionType.END_TURN: 9,
}


def choose_action(state: GameState, actions: List[Action], rng: random.Random) -> Action:
    """Pick the highest-priority action class, then choose within it at random.
    Robber moves prefer hexes that actually steal from the opponent."""
    best = min(_PRIORITY[a.type] for a in actions)
    pool = [a for a in actions if _PRIORITY[a.type] == best]
    if pool[0].type == ActionType.MOVE_ROBBER:
        pid = pool[0].player
        stealing = [
            a for a in pool
            if any(v in state.buildings and state.buildings[v][0] != pid
                   for v in state.board.get_vertices_for_hex(a.value))
        ]
        if stealing:
            pool = stealing
    return rng.choice(pool)
