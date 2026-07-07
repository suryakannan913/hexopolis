"""API layer tests — the routes are a thin adapter over app.engine."""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _create(seed=99, name="Alice"):
    resp = client.post("/game/new", json={"player_name": name, "seed": seed})
    assert resp.status_code == 201
    return resp.json()


def _act(game_id, index):
    resp = client.post(f"/game/{game_id}/action", json={"index": index})
    assert resp.status_code == 200
    return resp.json()


def _find(state, action_type):
    return [a for a in state["legal_actions"] if a["type"] == action_type]


def _through_setup(state):
    """Complete the snake draft: P0 pair, AI pair+pair, P0 pair."""
    gid = state["game_id"]
    state = _act(gid, 0)  # P0 settlement
    state = _act(gid, 0)  # P0 road
    state = client.post(f"/game/{gid}/ai-turn").json()  # AI places both pairs
    state = _act(gid, 0)  # P0 second settlement
    state = _act(gid, 0)  # P0 second road
    return state


class TestGameAPI:
    def test_health(self):
        assert client.get("/health").json()["status"] == "ok"

    def test_create_game_returns_state_with_legal_actions(self):
        state = _create()
        assert state["phase"] == "setup_settlement"
        assert len(state["hexes"]) == 19
        assert len(state["ports"]) == 9
        assert len(state["legal_actions"]) == 54
        assert state["players"][0]["name"] == "Alice"

    def test_same_seed_same_board(self):
        a, b = _create(seed=123), _create(seed=123)
        assert a["hexes"] == b["hexes"]
        assert a["ports"] == b["ports"]

    def test_missing_game_404(self):
        assert client.get("/game/nope").status_code == 404

    def test_bad_action_index_400(self):
        state = _create()
        resp = client.post(f"/game/{state['game_id']}/action", json={"index": 9999})
        assert resp.status_code == 400

    def test_setup_flow_reaches_main_phase(self):
        state = _through_setup(_create(seed=7))
        assert state["phase"] == "main"
        assert state["current_player"] == 0
        assert state["turn_number"] == 1
        # both players placed 2 settlements + 2 roads
        assert len(state["buildings"]) == 4
        assert len(state["roads"]) == 4

    def test_roll_build_end_turn_cycle(self):
        state = _through_setup(_create(seed=7))
        gid = state["game_id"]
        rolls = _find(state, "roll")
        assert len(rolls) == 1
        state = _act(gid, rolls[0]["index"])
        assert state["last_roll"] is not None
        if state["phase"] == "main":  # a 7 would detour through the robber flow
            ends = _find(state, "end_turn")
            state = _act(gid, ends[0]["index"])
            assert state["current_player"] == 1

    def test_ai_turn_plays_back_to_human(self):
        state = _through_setup(_create(seed=7))
        gid = state["game_id"]
        state = _act(gid, _find(state, "roll")[0]["index"])
        if state["phase"] == "main":
            state = _act(gid, _find(state, "end_turn")[0]["index"])
            state = client.post(f"/game/{gid}/ai-turn").json()
            assert state["winner"] is not None or state["actor"] == 0
