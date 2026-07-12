"""Event-sourced persistence: codec roundtrip, replay determinism, restart survival."""
import pytest
from fastapi.testclient import TestClient

from app import persistence
from app.engine import legal_actions, new_game, apply_action
from app.engine.policy import choose_action


def _client():
    from main import app
    return TestClient(app)


def _play_plies(client, gid, n):
    """Advance a game n human decisions (AI auto-plays in between)."""
    for _ in range(n):
        s = client.get(f"/game/{gid}").json()
        if s["winner"] is not None:
            break
        if s["actor"] == 0:
            client.post(f"/game/{gid}/action", json={"index": 0})
        else:
            client.post(f"/game/{gid}/ai-turn")


class TestActionCodec:
    def test_every_action_type_survives_roundtrip(self):
        """Play a long seeded self-play game; every applied action must decode
        back to an equal Action."""
        import random
        state = new_game(("A", "B"), seed=11)
        rng = random.Random(11)
        seen = set()
        for _ in range(3000):
            if state.is_terminal():
                break
            action = choose_action(state, legal_actions(state), rng)
            decoded = persistence.action_from_json(
                action.player, action.type.value, persistence.action_to_json(action))
            assert decoded == action
            seen.add(action.type)
            apply_action(state, action, validate=False)
        assert len(seen) >= 6  # the game exercised a real variety of actions


class TestRestartSurvival:
    def test_state_identical_after_cache_wipe(self):
        """The whole point: wipe the in-memory cache (a 'restart') and the
        replayed state must serialize identically — including RNG-dependent
        history (dice, steals, dev draws) and AI-turn interleaving."""
        from app.routes.game import games_db
        client = _client()
        gid = client.post("/game/new", json={"player_name": "T", "seed": 5}).json()["game_id"]
        _play_plies(client, gid, 25)
        before = client.get(f"/game/{gid}").json()

        games_db.clear()  # simulate a server restart
        after = client.get(f"/game/{gid}").json()
        assert after == before

    def test_game_continues_correctly_after_reload(self):
        from app.routes.game import games_db
        client = _client()
        gid = client.post("/game/new", json={"player_name": "T", "seed": 9}).json()["game_id"]
        _play_plies(client, gid, 10)
        games_db.clear()
        # Must still be able to act on the replayed state.
        s = client.get(f"/game/{gid}").json()
        if s["actor"] == 0 and s["winner"] is None:
            r = client.post(f"/game/{gid}/action", json={"index": 0})
            assert r.status_code == 200

    def test_unknown_game_404(self):
        assert _client().get("/game/nope").status_code == 404


class TestLogEndpoint:
    def test_log_matches_played_actions(self):
        client = _client()
        gid = client.post("/game/new", json={"player_name": "T", "seed": 5}).json()["game_id"]
        _play_plies(client, gid, 6)
        log = client.get(f"/game/{gid}/log").json()
        assert log["seed"] == 5
        assert len(log["actions"]) > 0
        assert [a["ply"] for a in log["actions"]] == list(range(len(log["actions"])))

    def test_ai_turn_reports_steps(self):
        client = _client()
        gid = client.post("/game/new", json={"player_name": "T", "seed": 5}).json()["game_id"]
        # Human's first setup pair, then the AI's turn must report its steps.
        client.post(f"/game/{gid}/action", json={"index": 0})
        client.post(f"/game/{gid}/action", json={"index": 0})
        r = client.post(f"/game/{gid}/ai-turn").json()
        assert "steps" in r and len(r["steps"]) >= 2  # AI placed settlements+roads
        assert all(s["player"] == 1 for s in r["steps"])
