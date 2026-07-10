"""Trainer tests: flat Monte Carlo recommender, MCTS, and the rollout policy."""
import random

import pytest

from app.engine import CITY, SETTLEMENT, Phase, apply_action, legal_actions, new_game
from app.engine.actions import Action, ActionType
from app.models.board import Resource
from app.trainer import mcts_recommend, recommend
from app.trainer.rollout_policy import weighted_random_policy


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
