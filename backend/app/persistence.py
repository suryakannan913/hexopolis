"""Event-sourced game persistence.

The engine is fully deterministic given (seed, action sequence) — proven by
the headless reproducibility check — so a game's durable form is just its
seed plus an append-only action log. Any state is rebuilt by replay. This
buys restart survival, a true ordered event history, and post-game review
without ever serializing engine state.

SQLite via the stdlib; one connection per operation (safe under FastAPI's
threadpool). DB path comes from HEXOPOLIS_DB (tests point it at a temp file).
"""
import json
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

from app.engine import apply_action, new_game
from app.engine.actions import Action, ActionType
from app.engine.state import GameState
from app.models.board import Edge, HexCoord, Resource, Vertex

_SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    seed INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'easy',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS actions (
    game_id TEXT NOT NULL REFERENCES games(id),
    ply INTEGER NOT NULL,
    player INTEGER NOT NULL,
    type TEXT NOT NULL,
    value TEXT NOT NULL,        -- JSON payload, decoded by action type
    PRIMARY KEY (game_id, ply)
);
"""


def _db_path() -> str:
    return os.environ.get(
        "HEXOPOLIS_DB",
        str(Path(__file__).resolve().parent.parent / "data" / "hexopolis.db"),
    )


def _connect() -> sqlite3.Connection:
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    return conn


# ---- action codec: Action <-> JSON, decoded by action type ----

def action_to_json(a: Action) -> str:
    v = a.value
    if isinstance(v, Vertex):
        payload = sorted([c.q, c.r] for c in v.hex_coords)
    elif isinstance(v, Edge):
        payload = sorted([[v.hex1.q, v.hex1.r], [v.hex2.q, v.hex2.r]])
    elif isinstance(v, HexCoord):
        payload = [v.q, v.r]
    elif isinstance(v, Resource):
        payload = v.value
    elif isinstance(v, tuple):
        payload = [r.value for r in v]
    else:
        payload = None
    return json.dumps(payload)


def action_from_json(player: int, type_: str, raw: str) -> Action:
    t = ActionType(type_)
    v = json.loads(raw)
    if t in (ActionType.BUILD_SETTLEMENT, ActionType.BUILD_CITY):
        value = Vertex(tuple(HexCoord(q, r) for q, r in v))
    elif t == ActionType.BUILD_ROAD:
        value = Edge(HexCoord(*v[0]), HexCoord(*v[1]))
    elif t == ActionType.MOVE_ROBBER:
        value = HexCoord(*v)
    elif t in (ActionType.DISCARD, ActionType.PLAY_MONOPOLY):
        value = Resource(v)
    elif t == ActionType.PLAY_YEAR_OF_PLENTY:
        value = tuple(Resource(r) for r in v)
    elif t == ActionType.MARITIME_TRADE:
        value = (Resource(v[0]), Resource(v[1]))
    else:
        value = None
    return Action(player=player, type=t, value=value)


# ---- store operations ----

def save_game(game_id: str, seed: int, player_name: str, difficulty: str) -> None:
    with _connect() as c:
        c.execute("INSERT OR REPLACE INTO games VALUES (?,?,?,?,CURRENT_TIMESTAMP)",
                  (game_id, seed, player_name, difficulty))


def append_action(game_id: str, ply: int, action: Action) -> None:
    with _connect() as c:
        c.execute("INSERT INTO actions VALUES (?,?,?,?,?)",
                  (game_id, ply, action.player, action.type.value, action_to_json(action)))


def load_game(game_id: str) -> Optional[Tuple[int, str, str, List[Action]]]:
    """Return (seed, player_name, difficulty, actions) or None if unknown."""
    with _connect() as c:
        row = c.execute("SELECT seed, player_name, difficulty FROM games WHERE id=?",
                        (game_id,)).fetchone()
        if row is None:
            return None
        acts = [
            action_from_json(p, t, v)
            for p, t, v in c.execute(
                "SELECT player, type, value FROM actions WHERE game_id=? ORDER BY ply",
                (game_id,))
        ]
    return row[0], row[1], row[2], acts


def replay(seed: int, player_name: str, actions: List[Action]) -> GameState:
    """Rebuild a state by replaying its action log from the seed."""
    state = new_game((player_name, "AI Opponent"), seed=seed)
    for a in actions:
        apply_action(state, a, validate=False)
    return state
