"""Probabilistic outcome expansion — port of catanatron's execute_spectrum
(BOT_LOGIC_REFERENCE.md §5, tree_search_utils).

expand(state, action) turns one action into [(child_state, probability), ...]:

- ROLL: 11 outcomes (sums 2-12) weighted by exact 2d6 probability. Dice are
  forced through a scripted RNG so the engine's own roll handler runs
  unchanged (discard quotas, robber phase, production).
- MOVE_ROBBER with a steal: one outcome per resource the victim holds,
  weighted by their hand proportions. DEVIATION (improvement, flagged by the
  source's own doc as its simplification): catanatron weights types uniformly
  at 1/5; our engine steals card-frequency-weighted, so the spectrum matches
  the true distribution exactly.
- BUY_DEV_CARD: one outcome per distinct card type remaining, weighted by
  deck composition — forced by swapping a card of that type to the top of the
  COPY's deck. The engine's deck order is real state, but honest search must
  not peek at it; enumerating by composition matches the source's
  "good card-counting, bank visible" assumption.
- Everything else: deterministic, probability 1.

Children get fresh real RNGs afterward so later (unenumerated) randomness
cannot silently replay the parent's stream.
"""
import random
from typing import List, Tuple

from app.engine import apply_action
from app.engine.actions import Action, ActionType
from app.engine.state import GameState
from app.models.board import Resource
from app.trainer.value_function import number_probability


class _ScriptedRng(random.Random):
    """Feeds predetermined outcomes to the engine's rng calls, then raises —
    inside spectrum expansion every stochastic call must be enumerated, so an
    unscripted draw means a rules/spectrum drift we want to hear about."""

    def __init__(self, ints=(), choices=()):
        super().__init__(0)
        self._ints = list(ints)
        self._choices = list(choices)

    def randint(self, a, b):
        if not self._ints:
            raise RuntimeError("spectrum: unscripted randint call")
        return self._ints.pop(0)

    def choice(self, seq):
        if not self._choices:
            raise RuntimeError("spectrum: unscripted choice call")
        forced = self._choices.pop(0)
        assert forced in seq, "forced steal outcome not in the victim's pool"
        return forced


def _child(state: GameState, action: Action, rng: random.Random) -> GameState:
    sim = state.copy()
    sim.rng = rng
    apply_action(sim, action, validate=False)
    sim.rng = random.Random(0)  # deterministic placeholder; see module docstring
    return sim


def _steal_victim(state: GameState, action: Action):
    """Mirror the engine's victim rule for a robber move (1v1: at most one)."""
    pid = action.player
    victims = sorted({
        state.buildings[v][0]
        for v in state.board.get_vertices_for_hex(action.value)
        if v in state.buildings and state.buildings[v][0] != pid
    })
    victims = [o for o in victims if state.players[o].hand_size() > 0]
    return state.players[victims[0]] if victims else None


def expand(state: GameState, action: Action) -> List[Tuple[GameState, float]]:
    """All possible resulting states of `action` with their probabilities."""
    if action.type == ActionType.ROLL:
        out = []
        for total in range(2, 13):
            d1 = max(1, total - 6)
            dice = _ScriptedRng(ints=[d1, total - d1])
            out.append((_child(state, action, dice), number_probability(total)))
        return out

    if action.type == ActionType.MOVE_ROBBER:
        victim = _steal_victim(state, action)
        if victim is None:
            return [(_child(state, action, _ScriptedRng()), 1.0)]
        hand = victim.hand_size()
        return [
            (_child(state, action, _ScriptedRng(choices=[r])), victim.resources[r] / hand)
            for r in Resource if victim.resources[r] > 0
        ]

    if action.type == ActionType.BUY_DEV_CARD:
        deck = state.dev_deck
        out = []
        for card in sorted(set(deck), key=lambda c: c.value):
            sim = state.copy()
            sim.rng = _ScriptedRng()
            idx = sim.dev_deck.index(card)
            sim.dev_deck[0], sim.dev_deck[idx] = sim.dev_deck[idx], sim.dev_deck[0]
            apply_action(sim, action, validate=False)
            sim.rng = random.Random(0)
            out.append((sim, deck.count(card) / len(deck)))
        return out

    return [(_child(state, action, _ScriptedRng()), 1.0)]
