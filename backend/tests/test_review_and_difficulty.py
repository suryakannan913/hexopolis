"""D-pass features: AI difficulty tiers and the post-game review endpoint."""
import pytest
from fastapi.testclient import TestClient


def _client():
    from main import app
    return TestClient(app)


def _play(client, gid, human_decisions):
    for _ in range(human_decisions):
        s = client.get(f"/game/{gid}").json()
        if s["winner"] is not None:
            break
        if s["actor"] == 0:
            client.post(f"/game/{gid}/action", json={"index": 0})
        else:
            client.post(f"/game/{gid}/ai-turn")


class TestDifficulty:
    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_ai_plays_at_every_difficulty(self, difficulty):
        client = _client()
        gid = client.post("/game/new", json={
            "player_name": "T", "seed": 13, "difficulty": difficulty}).json()["game_id"]
        _play(client, gid, 8)
        s = client.get(f"/game/{gid}").json()
        assert s["difficulty"] == difficulty
        # The AI actually took its setup + turns.
        assert any(b["owner"] == 1 for b in s["buildings"])

    def test_invalid_difficulty_rejected(self):
        r = _client().post("/game/new", json={"player_name": "T", "difficulty": "impossible"})
        assert r.status_code == 400

    def test_hard_ai_survives_restart_replay(self):
        """Trainer-driven AI moves must be replay-safe (no state.rng draws)."""
        from app.routes.game import games_db
        client = _client()
        gid = client.post("/game/new", json={
            "player_name": "T", "seed": 21, "difficulty": "hard"}).json()["game_id"]
        _play(client, gid, 6)
        before = client.get(f"/game/{gid}").json()
        games_db.clear()
        assert client.get(f"/game/{gid}").json() == before


class TestReview:
    def test_review_covers_human_decisions(self):
        client = _client()
        gid = client.post("/game/new", json={"player_name": "T", "seed": 5}).json()["game_id"]
        _play(client, gid, 15)
        r = client.get(f"/game/{gid}/review")
        assert r.status_code == 200
        body = r.json()
        assert body["summary"]["total"] == len(body["decisions"])
        for d in body["decisions"]:
            assert d["rank"] is not None and 1 <= d["rank"] <= d["n_options"]
            assert d["n_options"] >= 2
        s = body["summary"]
        assert s["best"] + s["fine"] + s["weak"] == s["total"]

    def test_review_of_fresh_game_is_empty(self):
        client = _client()
        gid = client.post("/game/new", json={"player_name": "T", "seed": 5}).json()["game_id"]
        body = client.get(f"/game/{gid}/review").json()
        assert body["decisions"] == []
