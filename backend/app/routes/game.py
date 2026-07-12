"""Thin HTTP adapter over the engine — no rules live here.

The client reads the serialized state (which includes the indexed
legal-action list) and submits an action by index. The AI opponent is a
simple heuristic policy stepped server-side.

NOTE: this is an action-based API; the pre-engine frontend spoke an older
contract and needs rework before it can drive this (tracked in ROADMAP.md).
"""
import random
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import persistence
from app.engine import GameState, apply_action, legal_actions, longest_road_length, new_game
from app.engine.actions import Action
from app.engine.policy import choose_action
from app.models.board import Edge, HexCoord, Resource, Vertex
from app.trainer import alphabeta_recommend, mcts_recommend, recommend, value_recommend

router = APIRouter(prefix="/game", tags=["game"])


@dataclass
class GameRecord:
    state: GameState
    ply: int            # actions applied so far (next action's index in the log)
    difficulty: str


# In-memory cache over the event-sourced store: a cache miss (e.g. after a
# server restart) rebuilds the state by replaying the persisted action log.
games_db: Dict[str, GameRecord] = {}


class GameCreateRequest(BaseModel):
    player_name: str
    seed: Optional[int] = None
    difficulty: str = "easy"


class ActionRequest(BaseModel):
    index: int  # index into the legal_actions list of the current state


def _get(game_id: str) -> GameRecord:
    rec = games_db.get(game_id)
    if rec is None:
        stored = persistence.load_game(game_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="Game not found")
        seed, name, difficulty, actions = stored
        rec = GameRecord(persistence.replay(seed, name, actions), len(actions), difficulty)
        games_db[game_id] = rec
    return rec


def _apply_and_record(game_id: str, rec: GameRecord, action: Action) -> None:
    apply_action(rec.state, action, validate=False)
    persistence.append_action(game_id, rec.ply, action)
    rec.ply += 1


def _policy_rng(seed: int, ply: int) -> random.Random:
    """Deterministic per-decision RNG for the AI policy, independent of the
    game's own stream (see the replay-divergence note in ai_turn)."""
    return random.Random(seed * 1_000_003 + ply)


def _json_value(x: Any) -> Any:
    if isinstance(x, Vertex):
        return {"vertex": sorted([c.q, c.r] for c in x.hex_coords)}
    if isinstance(x, Edge):
        return {"edge": sorted([[x.hex1.q, x.hex1.r], [x.hex2.q, x.hex2.r]])}
    if isinstance(x, HexCoord):
        return {"hex": [x.q, x.r]}
    if isinstance(x, Resource):
        return x.value
    if isinstance(x, tuple):
        return [_json_value(i) for i in x]
    return x


def _serialize(game_id: str, state: GameState) -> dict:
    return {
        "game_id": game_id,
        "seed": state.seed,
        "phase": state.phase.value,
        "current_player": state.current_player,
        "actor": state.actor() if not state.is_terminal() else None,
        "turn_number": state.turn_number,
        "has_rolled": state.has_rolled,
        "last_roll": list(state.last_roll) if state.last_roll else None,
        "winner": state.winner,
        "robber": [state.robber.q, state.robber.r],
        "bank": {r.value: n for r, n in state.bank.items()},
        "dev_deck_remaining": len(state.dev_deck),
        "hexes": [
            {"q": h.coord.q, "r": h.coord.r,
             "resource": h.resource.value if h.resource else None,
             "number": h.dice_number}
            for h in state.board.hexes.values()
        ],
        "ports": [
            {"vertex": _json_value(v)["vertex"], "type": t.value if t else "3:1"}
            for v, t in state.ports.items()
        ],
        "buildings": [
            {"vertex": _json_value(v)["vertex"], "owner": o, "kind": k}
            for v, (o, k) in state.buildings.items()
        ],
        "roads": [
            {"edge": _json_value(e)["edge"], "owner": o}
            for e, o in state.roads.items()
        ],
        "discard_quota": list(state.discard_quota),
        "players": [
            {
                "id": p.id, "name": p.name,
                "resources": {r.value: n for r, n in p.resources.items()},
                "dev_cards": {c.value: n for c, n in p.dev_hand.items()},
                "knights_played": p.knights_played,
                "roads_left": p.roads_left,
                "settlements_left": p.settlements_left,
                "cities_left": p.cities_left,
                "visible_vp": state.visible_vp(p.id),
                "total_vp": state.total_vp(p.id),
                "longest_road": longest_road_length(state, p.id),
            }
            for p in state.players
        ],
        "longest_road_owner": state.longest_road_owner,
        "largest_army_owner": state.largest_army_owner,
        "legal_actions": [
            {"index": i, "player": a.player, "type": a.type.value, "value": _json_value(a.value)}
            for i, a in enumerate(legal_actions(state))
        ],
    }


@router.post("/new", status_code=201)
def create_game(request: GameCreateRequest):
    if request.difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=400, detail="difficulty must be easy, medium, or hard")
    game_id = uuid.uuid4().hex[:8]
    state = new_game((request.player_name, "AI Opponent"), seed=request.seed)
    games_db[game_id] = GameRecord(state, 0, request.difficulty)
    persistence.save_game(game_id, state.seed, request.player_name, request.difficulty)
    return _serialize(game_id, state)


@router.get("/{game_id}")
def get_state(game_id: str):
    return _serialize(game_id, _get(game_id).state)


@router.get("/{game_id}/log")
def get_log(game_id: str):
    """Ordered action history (the game's durable, replayable form)."""
    _get(game_id)  # 404 if unknown
    stored = persistence.load_game(game_id)
    seed, name, difficulty, actions = stored
    return {
        "game_id": game_id, "seed": seed, "player_name": name, "difficulty": difficulty,
        "actions": [
            {"ply": i, "player": a.player, "type": a.type.value, "value": _json_value(a.value)}
            for i, a in enumerate(actions)
        ],
    }


@router.post("/{game_id}/action")
def post_action(game_id: str, request: ActionRequest):
    rec = _get(game_id)
    acts = legal_actions(rec.state)
    if not 0 <= request.index < len(acts):
        raise HTTPException(status_code=400, detail=f"action index out of range (0..{len(acts)-1})")
    _apply_and_record(game_id, rec, acts[request.index])
    return _serialize(game_id, rec.state)


@router.get("/{game_id}/recommend")
def recommend_moves(game_id: str, tier: str = "mc", sims: Optional[int] = None,
                    seed: Optional[int] = None, depth: int = 2):
    """Trainer endpoint: rank the current actor's legal actions.

    tier=value      instant 1-ply heuristic (returns `score`, not a probability)
    tier=mc         flat Monte Carlo (`sims` = rollouts per action, default 25)
    tier=mcts       UCB1 tree search (`sims` = total simulations, default 200)
    tier=alphabeta  expectiminimax (`depth`, default 2; returns `score`)

    Monte Carlo tiers take seconds; `index` matches the state's legal_actions
    list, so a client can act on a recommendation via POST /action directly.
    The game state is not mutated.
    """
    state = _get(game_id).state
    if state.is_terminal():
        raise HTTPException(status_code=400, detail="Game is over")
    index_of = {a: i for i, a in enumerate(legal_actions(state))}

    if tier == "value":
        items = [
            {"index": index_of[r.action], "type": r.action.type.value,
             "value": _json_value(r.action.value), "score": r.score}
            for r in value_recommend(state, seed=seed)
        ]
    elif tier == "mc":
        items = [
            {"index": index_of[r.action], "type": r.action.type.value,
             "value": _json_value(r.action.value),
             "win_probability": r.win_probability, "sims": r.sims}
            for r in recommend(state, sims_per_action=sims or 25, seed=seed)
        ]
    elif tier == "mcts":
        items = [
            {"index": index_of[r.action], "type": r.action.type.value,
             "value": _json_value(r.action.value),
             "win_probability": r.win_probability, "sims": r.sims}
            for r in mcts_recommend(state, num_simulations=sims or 200, seed=seed)
        ]
    elif tier == "alphabeta":
        items = [
            {"index": index_of[r.action], "type": r.action.type.value,
             "value": _json_value(r.action.value), "score": r.score}
            for r in alphabeta_recommend(state, depth=depth)
        ]
    else:
        raise HTTPException(status_code=400, detail="tier must be value, mc, mcts, or alphabeta")

    return {"game_id": game_id, "tier": tier, "advising": state.actor(),
            "recommendations": items}


@router.post("/{game_id}/ai-turn")
def ai_turn(game_id: str):
    """Step the AI (player 1) until control returns to player 0 or the game
    ends. Stops early if player 0 must decide (e.g. a discard). The response
    includes `steps` — each action the AI took, in order — so clients can
    show a true play-by-play instead of diffing states."""
    rec = _get(game_id)
    state = rec.state
    steps = []
    while not state.is_terminal() and state.actor() == 1 and len(steps) < 10_000:
        acts = legal_actions(state)
        # Policy randomness must NOT come from state.rng: replay applies the
        # logged actions without re-deciding, so any policy draws taken from
        # the game stream would make live and replayed dice diverge. A fresh
        # RNG keyed by (seed, ply) is deterministic and stream-independent.
        action = choose_action(state, acts, _policy_rng(state.seed, rec.ply))
        _apply_and_record(game_id, rec, action)
        steps.append(action)
    out = _serialize(game_id, state)
    out["steps"] = [
        {"player": a.player, "type": a.type.value, "value": _json_value(a.value)}
        for a in steps
    ]
    return out
