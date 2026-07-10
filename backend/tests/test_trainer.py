"""Trainer tests: flat MC recommender, MCTS, value function, rollout policy, API."""
import random

import pytest
from fastapi.testclient import TestClient

from app.engine import CITY, SETTLEMENT, Phase, apply_action, legal_actions, new_game
from app.engine.actions import Action, ActionType
from app.engine.state import PlayerState
from app.models.board import Resource
from app.trainer import alphabeta_recommend, mcts_recommend, recommend, value_recommend
from app.trainer.rollout_policy import weighted_random_policy
from app.trainer.spectrum import expand
from app.trainer.value_function import (
    effective_production,
    hand_synergy,
    number_probability,
)


def _main_phase_state(seed=7):
    """Real game advanced through the setup snake draft; MAIN phase, roll pending."""
    state = new_game(("A", "B"), seed=seed)
    while state.phase in (Phase.SETUP_SETTLEMENT, Phase.SETUP_ROAD):
        apply_action(state, legal_actions(state)[0])
    assert state.phase == Phase.MAIN
    return state


def _winning_city_state():
    """P0 at 14 total VP where any BUILD_CITY reaches 15 and wins immediately.

    4 settlements (4) + 3 cities (6) + Longest Road (2) + Largest Army (2) = 14.
    A city upgrade nets +1 VP (settlement -1, city +2) -> 15.
    """
    state = _main_phase_state()
    free = [v for v in state.board.get_all_vertices() if v not in state.buildings]
    for v in free[:2]:
        state.buildings[v] = (0, SETTLEMENT)   # 2 from setup + 2 injected = 4
    for v in free[2:5]:
        state.buildings[v] = (0, CITY)
    state.longest_road_owner = 0
    state.largest_army_owner = 0
    p0 = state.players[0]
    p0.settlements_left, p0.cities_left = 1, 1
    p0.resources[Resource.ORE] = 3
    p0.resources[Resource.WHEAT] = 2
    state.has_rolled = True                    # build actions are now legal
    assert state.total_vp(0) == 14
    return state


class TestFlatMonteCarlo:
    def test_immediate_win_anchor(self):
        """Every city upgrade wins on the spot -> probability exactly 1.0, ranked first."""
        state = _winning_city_state()
        recs = recommend(state, sims_per_action=5, seed=1)
        city_recs = [r for r in recs if r.action.type == ActionType.BUILD_CITY]
        assert city_recs, "city upgrades must be legal in this position"
        assert all(r.win_probability == 1.0 for r in city_recs)
        assert recs[0].win_probability == 1.0

    def test_covers_all_legal_actions_with_valid_probabilities(self):
        state = _winning_city_state()
        recs = recommend(state, sims_per_action=2, seed=3)
        assert {r.action for r in recs} == set(legal_actions(state))
        assert all(0.0 <= r.win_probability <= 1.0 for r in recs)
        probs = [r.win_probability for r in recs]
        assert probs == sorted(probs, reverse=True)

    def test_seeded_recommendation_is_reproducible(self):
        state = _main_phase_state()
        a = recommend(state, sims_per_action=3, seed=42)
        b = recommend(state, sims_per_action=3, seed=42)
        assert a == b

    def test_does_not_mutate_input_state(self):
        state = _main_phase_state()
        before = (state.phase, dict(state.buildings), dict(state.roads),
                  state.turn_number, state.rng.getstate())
        recommend(state, sims_per_action=2, seed=0)
        after = (state.phase, dict(state.buildings), dict(state.roads),
                 state.turn_number, state.rng.getstate())
        assert before == after

    def test_ply_cap_censors_unfinished_rollouts_as_losses(self):
        state = _main_phase_state()
        recs = recommend(state, sims_per_action=2, seed=0, ply_cap=1)
        assert all(r.win_probability == 0.0 for r in recs)

    def test_terminal_state_rejected(self):
        state = _winning_city_state()
        city = next(a for a in legal_actions(state) if a.type == ActionType.BUILD_CITY)
        apply_action(state, city)
        assert state.is_terminal()
        with pytest.raises(ValueError):
            recommend(state)


class TestMCTS:
    def test_immediate_win_anchor(self):
        state = _winning_city_state()
        recs = mcts_recommend(state, num_simulations=60, seed=2)
        assert {r.action for r in recs} == set(legal_actions(state))
        city_recs = [r for r in recs if r.action.type == ActionType.BUILD_CITY]
        assert all(r.win_probability == 1.0 for r in city_recs if r.sims > 0)
        assert recs[0].win_probability == 1.0

    def test_seeded_mcts_is_reproducible(self):
        state = _winning_city_state()
        a = mcts_recommend(state, num_simulations=30, seed=9)
        b = mcts_recommend(state, num_simulations=30, seed=9)
        assert a == b

    def test_does_not_mutate_input_state(self):
        state = _winning_city_state()
        before = (state.phase, dict(state.buildings), state.rng.getstate())
        mcts_recommend(state, num_simulations=20, seed=0)
        after = (state.phase, dict(state.buildings), state.rng.getstate())
        assert before == after


class TestValueFunction:
    def test_number_probability_is_exact_2d6(self):
        assert number_probability(2) == number_probability(12) == 1 / 36
        assert number_probability(7) == 6 / 36
        assert sum(number_probability(n) for n in range(2, 13)) == pytest.approx(1.0)

    def test_robber_suppresses_production(self):
        state = _main_phase_state()
        base = sum(effective_production(state, 0).values())
        # Park the robber on a producing hex adjacent to one of P0's buildings.
        target = next(
            h.coord
            for v, (o, _) in state.buildings.items() if o == 0
            for h in state.board.get_hexes_for_vertex(v)
            if h.resource is not None and h.dice_number is not None
        )
        state.robber = target
        assert sum(effective_production(state, 0).values()) < base

    def test_hand_synergy_bounds(self):
        empty = PlayerState(id=0, name="x")
        assert hand_synergy(empty) == 0.0
        full = PlayerState(id=0, name="y")
        for r, n in [(Resource.WHEAT, 2), (Resource.ORE, 3), (Resource.WOOD, 1),
                     (Resource.BRICK, 1), (Resource.SHEEP, 1)]:
            full.resources[r] = n
        assert hand_synergy(full) == 1.0

    def test_immediate_win_anchor(self):
        """The near-lexicographic VP term must put a winning city upgrade first."""
        state = _winning_city_state()
        scored = value_recommend(state, seed=5)
        assert scored[0].action.type == ActionType.BUILD_CITY
        assert {s.action for s in scored} == set(legal_actions(state))

    def test_seeded_value_recommend_is_reproducible(self):
        state = _main_phase_state()
        assert value_recommend(state, seed=11) == value_recommend(state, seed=11)

    def test_does_not_mutate_input_state(self):
        state = _main_phase_state()
        before = (state.phase, dict(state.buildings), state.rng.getstate())
        value_recommend(state, seed=0)
        after = (state.phase, dict(state.buildings), state.rng.getstate())
        assert before == after


class TestSpectrum:
    def test_roll_expands_to_eleven_weighted_outcomes(self):
        state = _main_phase_state()
        roll = next(a for a in legal_actions(state) if a.type == ActionType.ROLL)
        outcomes = expand(state, roll)
        assert len(outcomes) == 11
        assert sum(p for _, p in outcomes) == pytest.approx(1.0)
        sums = sorted(sum(child.last_roll) for child, _ in outcomes)
        assert sums == list(range(2, 13))
        for child, p in outcomes:
            assert p == number_probability(sum(child.last_roll))

    def test_deterministic_action_is_single_certain_outcome(self):
        state = _winning_city_state()
        city = next(a for a in legal_actions(state) if a.type == ActionType.BUILD_CITY)
        outcomes = expand(state, city)
        assert len(outcomes) == 1 and outcomes[0][1] == 1.0
        assert outcomes[0][0].is_terminal()          # the upgrade wins at 15 VP
        assert not state.is_terminal()               # parent untouched

    def test_buy_dev_card_weighted_by_deck_composition(self):
        state = _winning_city_state()
        p0 = state.players[0]
        p0.resources[Resource.ORE] += 1
        p0.resources[Resource.SHEEP] += 1
        p0.resources[Resource.WHEAT] += 1
        buy = next(a for a in legal_actions(state) if a.type == ActionType.BUY_DEV_CARD)
        outcomes = expand(state, buy)
        deck = state.dev_deck
        assert len(outcomes) == len(set(deck))
        assert sum(p for _, p in outcomes) == pytest.approx(1.0)
        for child, p in outcomes:
            drawn = next(c for c in child.players[0].dev_bought_this_turn
                         if child.players[0].dev_bought_this_turn[c]
                         > p0.dev_bought_this_turn[c])
            assert p == pytest.approx(deck.count(drawn) / len(deck))


class TestAlphaBeta:
    def test_immediate_win_anchor(self):
        state = _winning_city_state()
        scored = alphabeta_recommend(state, depth=2)
        assert scored[0].action.type == ActionType.BUILD_CITY
        assert scored[0].score == pytest.approx(1e18)   # explicit terminal win value
        assert {s.action for s in scored} == set(legal_actions(state))

    def test_is_deterministic(self):
        state = _main_phase_state()
        assert alphabeta_recommend(state, depth=1) == alphabeta_recommend(state, depth=1)

    def test_does_not_mutate_input_state(self):
        state = _winning_city_state()
        before = (state.phase, dict(state.buildings), state.rng.getstate())
        alphabeta_recommend(state, depth=1)
        after = (state.phase, dict(state.buildings), state.rng.getstate())
        assert before == after

    def test_rejects_bad_depth_and_terminal(self):
        state = _main_phase_state()
        with pytest.raises(ValueError):
            alphabeta_recommend(state, depth=0)
        won = _winning_city_state()
        city = next(a for a in legal_actions(won) if a.type == ActionType.BUILD_CITY)
        apply_action(won, city)
        with pytest.raises(ValueError):
            alphabeta_recommend(won)


class TestRecommendAPI:
    def _client_and_game(self):
        from main import app
        client = TestClient(app)
        game_id = client.post("/game/new", json={"player_name": "T", "seed": 7}).json()["game_id"]
        # Walk the setup snake draft (human + AI) to reach the main phase.
        for _ in range(20):
            s = client.get(f"/game/{game_id}").json()
            if s["phase"] not in ("setup_settlement", "setup_road"):
                break
            if s["actor"] == 0:
                client.post(f"/game/{game_id}/action", json={"index": 0})
            else:
                client.post(f"/game/{game_id}/ai-turn")
        return client, game_id

    def test_value_tier(self):
        client, gid = self._client_and_game()
        r = client.get(f"/game/{gid}/recommend", params={"tier": "value", "seed": 1})
        assert r.status_code == 200
        body = r.json()
        n_legal = len(client.get(f"/game/{gid}").json()["legal_actions"])
        assert len(body["recommendations"]) == n_legal
        scores = [x["score"] for x in body["recommendations"]]
        assert scores == sorted(scores, reverse=True)
        assert all(0 <= x["index"] < n_legal for x in body["recommendations"])

    def test_mc_tier_returns_probabilities(self):
        client, gid = self._client_and_game()
        r = client.get(f"/game/{gid}/recommend", params={"tier": "mc", "sims": 2, "seed": 1})
        assert r.status_code == 200
        for x in r.json()["recommendations"]:
            assert 0.0 <= x["win_probability"] <= 1.0
            assert x["sims"] == 2

    def test_alphabeta_tier(self):
        client, gid = self._client_and_game()
        r = client.get(f"/game/{gid}/recommend", params={"tier": "alphabeta", "depth": 1})
        assert r.status_code == 200
        scores = [x["score"] for x in r.json()["recommendations"]]
        assert scores and scores == sorted(scores, reverse=True)

    def test_unknown_tier_rejected(self):
        client, gid = self._client_and_game()
        assert client.get(f"/game/{gid}/recommend", params={"tier": "bogus"}).status_code == 400


class TestRolloutPolicy:
    def test_prefers_city_overwhelmingly(self):
        """WeightedRandomPlayer weights: city 10000 vs end_turn 1."""
        state = _main_phase_state()
        actions = [Action(0, ActionType.BUILD_CITY, None), Action(0, ActionType.END_TURN, None)]
        rng = random.Random(0)
        picks = [weighted_random_policy(state, actions, rng) for _ in range(200)]
        assert sum(1 for a in picks if a.type == ActionType.BUILD_CITY) >= 195

    def test_returns_member_of_action_list(self):
        state = _main_phase_state()
        acts = legal_actions(state)
        assert weighted_random_policy(state, acts, random.Random(1)) in acts
