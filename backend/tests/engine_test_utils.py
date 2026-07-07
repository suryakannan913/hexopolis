"""Shared helpers for engine tests: run phases, craft hands, find board spots."""
import random

from app.engine import Phase, apply_action, legal_actions, new_game
from app.models.board import Resource


def game(seed: int = 1):
    return new_game(("A", "B"), seed=seed)


def run_setup(state):
    """Drive the snake draft by always taking the first legal action."""
    while state.phase in (Phase.SETUP_SETTLEMENT, Phase.SETUP_ROAD):
        apply_action(state, legal_actions(state)[0], validate=False)
    return state


def main_phase_game(seed: int = 1, rolled: bool = True):
    """A game past setup, at the start of P0's first turn."""
    state = run_setup(game(seed))
    state.has_rolled = rolled  # skip the stochastic roll for crafted scenarios
    return state


def give(player, **amounts):
    """give(p, wood=2, ore=1) — add resources by name (bank not touched)."""
    for name, n in amounts.items():
        player.resources[Resource(name)] += n


def acts_of(state, action_type):
    return [a for a in legal_actions(state) if a.type == action_type]


def seed_rolling(total: int) -> random.Random:
    """An RNG whose next two randint(1,6) draws sum to `total`."""
    for k in range(10_000):
        r = random.Random(k)
        if r.randint(1, 6) + r.randint(1, 6) == total:
            return random.Random(k)
    raise AssertionError(f"no small seed rolls {total}")
