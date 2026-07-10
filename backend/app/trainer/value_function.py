"""Tier 3: hand-crafted value function + instant 1-ply recommender.

Port of catanatron ValueFunctionPlayer's base_fn (BOT_LOGIC_REFERENCE.md
§3.6), including both published weight sets (DEFAULT_WEIGHTS and the tuned
CONTENDER_WEIGHTS). The reference doc calls this formula 1v1-EXACT: its single
hardcoded "P1 enemy" slot is an approximation in 3-4 player games but is
literally the opponent here.

Scores are NOT win probabilities — the huge weight on victory points makes the
ordering near-lexicographic (first VPs, then production, then the rest). Use
this tier for instant hints; use the Monte Carlo tiers for probabilities.

Documented deviations from the source:
- Self VP term uses total_vp (includes own hidden VP dev cards). The source
  reads PUBLIC VPs despite its own "winning is best at all costs" comment — a
  quirk its reference doc flags; our win check is on total VP, so an evaluator
  blind to VP cards would miss actual wins.
- Discard-risk penalty triggers above OUR ruleset's 9-card limit (D2), not the
  base game's 7 the source assumes.
- Enemy production is computed directly for the opponent rather than via the
  source's redundant recompute-from-self's-perspective (flagged in the doc as
  wasteful-but-not-incorrect).
Not copied (per plan): nothing here reuses the source's dead-code FEATURES
reassignment or the MCTSScoreCollector army-size naming swap.
"""
import random
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.engine import apply_action, legal_actions, longest_road_length
from app.engine.actions import Action
from app.engine.rules import _road_edges, _settlement_vertices
from app.engine.state import CITY, DISCARD_LIMIT, GameState, PlayerState
from app.models.board import Resource

DEFAULT_WEIGHTS: Dict[str, float] = {
    "public_vps": 3e14,
    "production": 1e8,
    "enemy_production": -1e8,
    "num_tiles": 1,
    "reachable_production_0": 0,
    "reachable_production_1": 1e4,
    "buildable_nodes": 1e3,
    "longest_road": 10,
    "hand_synergy": 1e2,
    "hand_resources": 1,
    "discard_penalty": -5,
    "hand_devs": 10,
    "army_size": 10.1,
}

# Hyperparameter-search variant published alongside base_fn (§3.6).
CONTENDER_WEIGHTS: Dict[str, float] = {
    "public_vps": 300000000000001.94,
    "production": 100000002.04188395,
    "enemy_production": -99999998.03389844,
    "num_tiles": 2.91440418,
    "reachable_production_0": 2.03820085,
    "reachable_production_1": 10002.018773150001,
    "buildable_nodes": 1001.86278466,
    "longest_road": 12.127388499999999,
    "hand_synergy": 102.40606877,
    "hand_resources": 2.43644327,
    "discard_penalty": -3.00141993,
    "hand_devs": 10.721669799999999,
    "army_size": 12.93844622,
}

PROBA_POINT = 2.778 / 100   # ~1/36, the source's per-pip probability unit
TRANSLATE_VARIETY = 4       # bonus per distinct produced resource


def number_probability(n: int) -> float:
    """Exact 2d6 probability of rolling sum n (catanatron DICE_PROBAS)."""
    return (6 - abs(7 - n)) / 36


def effective_production(state: GameState, pid: int) -> Dict[Resource, float]:
    """Expected cards per roll by resource: settlements x1, cities x2,
    robber-occupied hexes contribute nothing."""
    prod: Dict[Resource, float] = {r: 0.0 for r in Resource}
    for v, (owner, kind) in state.buildings.items():
        if owner != pid:
            continue
        mult = 2 if kind == CITY else 1
        for h in state.board.get_hexes_for_vertex(v):
            if h.resource is not None and h.dice_number is not None and h.coord != state.robber:
                prod[h.resource] += mult * number_probability(h.dice_number)
    return prod


def production_value(prod: Dict[Resource, float], include_variety: bool) -> float:
    """Summed production plus (optionally) the variety bonus from the source's
    value_production: each distinct nonzero resource adds 4 * proba_point."""
    total = sum(prod.values())
    if include_variety:
        total += sum(1 for x in prod.values() if x > 0) * TRANSLATE_VARIETY * PROBA_POINT
    return total


def _vertex_production(state: GameState, v) -> float:
    """Expected production of a prospective settlement at vertex v."""
    return sum(
        number_probability(h.dice_number)
        for h in state.board.get_hexes_for_vertex(v)
        if h.resource is not None and h.dice_number is not None and h.coord != state.robber
    )


def hand_synergy(p: PlayerState) -> float:
    """0..1: how close the hand is to affording a city and a settlement."""
    r = p.resources
    distance_to_city = (max(2 - r[Resource.WHEAT], 0) + max(3 - r[Resource.ORE], 0)) / 5.0
    distance_to_settlement = (
        max(1 - r[Resource.WHEAT], 0) + max(1 - r[Resource.SHEEP], 0)
        + max(1 - r[Resource.BRICK], 0) + max(1 - r[Resource.WOOD], 0)
    ) / 4.0
    return (2 - distance_to_city - distance_to_settlement) / 2


def value_fn(state: GameState, pid: int, weights: Dict[str, float] = DEFAULT_WEIGHTS) -> float:
    """Score `state` from player `pid`'s perspective (higher is better)."""
    p = state.players[pid]

    buildable_now = _settlement_vertices(state, pid)          # 0 extra roads
    now_set = set(buildable_now)
    one_road_away = {                                          # exactly 1 more road
        v
        for e in _road_edges(state, pid)
        for v in state.board.get_edge_endpoints(e)
        if v not in now_set and v in state.board.get_all_vertices()
        and v not in state.buildings
    }

    own_tiles = {
        h.coord
        for v, (owner, _) in state.buildings.items() if owner == pid
        for h in state.board.get_hexes_for_vertex(v)
    }

    hand_size = p.hand_size()
    road_factor = weights["longest_road"] if not buildable_now else 0.1

    return (
        state.total_vp(pid) * weights["public_vps"]
        + production_value(effective_production(state, pid), True) * weights["production"]
        + production_value(effective_production(state, 1 - pid), False) * weights["enemy_production"]
        + sum(_vertex_production(state, v) for v in buildable_now) * weights["reachable_production_0"]
        + sum(_vertex_production(state, v) for v in one_road_away) * weights["reachable_production_1"]
        + hand_synergy(p) * weights["hand_synergy"]
        + len(buildable_now) * weights["buildable_nodes"]
        + len(own_tiles) * weights["num_tiles"]
        + hand_size * weights["hand_resources"]
        + (weights["discard_penalty"] if hand_size > DISCARD_LIMIT else 0)
        + longest_road_length(state, pid) * road_factor
        + sum(p.dev_hand.values()) * weights["hand_devs"]
        + p.knights_played * weights["army_size"]
    )


@dataclass(frozen=True)
class ScoredAction:
    action: Action
    score: float


def value_recommend(state: GameState, weights: Dict[str, float] = DEFAULT_WEIGHTS,
                    seed: Optional[int] = None) -> List[ScoredAction]:
    """1-ply greedy ranking (ValueFunctionPlayer.decide shape): simulate each
    legal action once — stochastic actions get one sampled outcome, as in the
    source — and rank resulting states by value_fn. Milliseconds, no rollouts.
    """
    if state.is_terminal():
        raise ValueError("game is over — nothing to recommend")
    advisee = state.actor()
    master = random.Random(seed)

    results = []
    for action in legal_actions(state):
        sim = state.copy()
        sim.rng = random.Random(master.randrange(2**63))
        apply_action(sim, action, validate=False)
        results.append(ScoredAction(action, value_fn(sim, advisee, weights)))

    results.sort(key=lambda r: r.score, reverse=True)
    return results
