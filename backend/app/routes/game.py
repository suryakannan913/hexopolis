"""Thin HTTP adapter over the engine — no rules live here.

The client reads the serialized state (which includes the indexed
legal-action list) and submits an action by index. The AI opponent is a
simple heuristic policy stepped server-side.

NOTE: this is an action-based API; the pre-engine frontend spoke an older
contract and needs rework before it can drive this (tracked in ROADMAP.md).
"""
import random
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.engine import GameState, apply_action, legal_actions, new_game
from app.engine.policy import choose_action
from app.models.board import Edge, HexCoord, Resource, Vertex

router = APIRouter(prefix="/game", tags=["game"])

games_db: Dict[str, GameState] = {}
_counter = 0


class GameCreateRequest(BaseModel):
    player_name: str
    seed: Optional[int] = None


class ActionRequest(BaseModel):
    index: int  # index into the legal_actions list of the current state


def _get(game_id: str) -> GameState:
    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game not found")
    return games_db[game_id]


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
    global _counter
    _counter += 1
    game_id = f"game-{_counter}"
    games_db[game_id] = new_game((request.player_name, "AI Opponent"), seed=request.seed)
    return _serialize(game_id, games_db[game_id])


@router.get("/{game_id}")
def get_state(game_id: str):
    return _serialize(game_id, _get(game_id))


@router.post("/{game_id}/action")
def post_action(game_id: str, request: ActionRequest):
    state = _get(game_id)
    acts = legal_actions(state)
    if not 0 <= request.index < len(acts):
        raise HTTPException(status_code=400, detail=f"action index out of range (0..{len(acts)-1})")
    apply_action(state, acts[request.index], validate=False)
    return _serialize(game_id, state)


@router.post("/{game_id}/ai-turn")
def ai_turn(game_id: str):
    """Step the heuristic AI (player 1) until control returns to player 0 or
    the game ends. Stops early if player 0 must decide (e.g. a discard)."""
    state = _get(game_id)
    steps = 0
    while not state.is_terminal() and state.actor() == 1 and steps < 10_000:
        acts = legal_actions(state)
        apply_action(state, choose_action(state, acts, state.rng), validate=False)
        steps += 1
    return _serialize(game_id, state)
