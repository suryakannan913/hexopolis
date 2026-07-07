"""Longest Road (§11), winning at 15 on your own turn (§12), determinism, copy()."""
import random

from app.engine import (
    ActionType,
    CITY,
    DevCard,
    Phase,
    SETTLEMENT,
    WINNING_POINTS,
    apply_action,
    legal_actions,
    longest_road_length,
    new_game,
)
from app.engine.policy import choose_action
from app.engine.rules import _maintain_longest_road
from app.engine.state import CITY_COST
from app.models.board import Edge, HexCoord, Vertex, Resource

from tests.engine_test_utils import acts_of, game, give, main_phase_game


def _ring_edges(n: int):
    """n consecutive edges around hex (0,0) — a connected chain."""
    center = HexCoord(0, 0)
    nbrs = center.neighbors()
    return [Edge(center, nbrs[i]) for i in range(n)]


def _chain_state(seed=1):
    s = main_phase_game(seed)
    s.buildings.clear()
    s.roads.clear()
    s.longest_road_owner = None
    return s


class TestLongestRoad:
    def test_four_roads_no_award(self):
        s = _chain_state()
        for e in _ring_edges(4):
            s.roads[e] = 0
        _maintain_longest_road(s, 0)
        assert longest_road_length(s, 0) == 4
        assert s.longest_road_owner is None

    def test_five_roads_awards_two_vp(self):
        s = _chain_state()
        for e in _ring_edges(5):
            s.roads[e] = 0
        _maintain_longest_road(s, 0)
        assert longest_road_length(s, 0) == 5
        assert s.longest_road_owner == 0
        assert s.visible_vp(0) == 2

    def test_transfer_only_on_strictly_longer(self):
        s = _chain_state()
        for e in _ring_edges(5):
            s.roads[e] = 0
        _maintain_longest_road(s, 0)
        # opponent ties with 5 around another hex: no transfer
        other = HexCoord(1, 1)
        nbrs = other.neighbors()
        for i in range(5):
            s.roads[Edge(other, nbrs[i])] = 1
        _maintain_longest_road(s, 1)
        assert s.longest_road_owner == 0
        # a sixth road: strictly longer, transfers
        s.roads[Edge(other, nbrs[5])] = 1
        _maintain_longest_road(s, 1)
        assert s.longest_road_owner == 1

    def test_opponent_settlement_breaks_the_path(self):
        s = _chain_state()
        edges = _ring_edges(5)
        for e in edges:
            s.roads[e] = 0
        _maintain_longest_road(s, 0)
        assert s.longest_road_owner == 0
        # settle P1 on the middle vertex of the chain: splits 5 into 2 + 3
        center = HexCoord(0, 0)
        nbrs = center.neighbors()
        mid = Vertex((center, nbrs[2], nbrs[3]))
        s.buildings[mid] = (1, SETTLEMENT)
        _maintain_longest_road(s, 1)
        assert longest_road_length(s, 0) == 3
        assert s.longest_road_owner is None  # set aside: nobody at 5+

    def test_break_transfers_if_opponent_qualifies(self):
        s = _chain_state()
        for e in _ring_edges(5):
            s.roads[e] = 0
        _maintain_longest_road(s, 0)
        other = HexCoord(1, 1)
        nbrs_o = other.neighbors()
        for i in range(5):
            s.roads[Edge(other, nbrs_o[i])] = 1
        _maintain_longest_road(s, 1)
        assert s.longest_road_owner == 0  # tie kept it
        center = HexCoord(0, 0)
        nbrs = center.neighbors()
        s.buildings[Vertex((center, nbrs[2], nbrs[3]))] = (1, SETTLEMENT)
        _maintain_longest_road(s, 1)
        assert s.longest_road_owner == 1  # holder broken below 5, opponent has 5


class TestWinning:
    def test_city_build_reaching_15_wins_immediately(self):
        s = main_phase_game()
        # craft: 3 cities + 4 settlements + LR + LA = 14 visible; a 4th city -> 15
        s.buildings.clear()
        verts = list(s.board.get_all_vertices())
        for v in verts[:3]:
            s.buildings[v] = (0, CITY)
        for v in verts[10:14]:
            s.buildings[v] = (0, SETTLEMENT)
        s.longest_road_owner = 0
        s.largest_army_owner = 0
        assert s.visible_vp(0) == 14
        give(s.players[0], ore=3, wheat=2)
        target = s.settlements_of(0)[0]
        act = next(a for a in acts_of(s, ActionType.BUILD_CITY) if a.value == target)
        apply_action(s, act)
        assert s.winner == 0
        assert s.is_terminal()
        assert legal_actions(s) == []

    def test_hidden_vp_card_can_complete_the_win(self):
        s = main_phase_game()
        s.buildings.clear()
        verts = list(s.board.get_all_vertices())
        for v in verts[:4]:
            s.buildings[v] = (0, CITY)
        for v in verts[10:14]:
            s.buildings[v] = (0, SETTLEMENT)
        s.longest_road_owner = 0
        assert s.visible_vp(0) == 14
        give(s.players[0], ore=1, sheep=1, wheat=1)
        s.dev_deck = [DevCard.VICTORY_POINT]
        apply_action(s, acts_of(s, ActionType.BUY_DEV_CARD)[0])
        assert s.total_vp(0) == 15
        assert s.winner == 0  # §12: reveal to win on your own turn

    def test_cannot_win_on_opponents_turn(self):
        s = main_phase_game()
        # P1 sits at 15 total VP, but it's P0's turn: no winner yet
        s.players[1].dev_hand[DevCard.VICTORY_POINT] = 13
        assert s.total_vp(1) == 15
        assert s.winner is None
        for r in Resource:
            s.players[0].resources[r] = 0
        apply_action(s, acts_of(s, ActionType.END_TURN)[0])
        assert s.winner is None  # still none: P1 hasn't acted
        # P1's first own action triggers the win check
        apply_action(s, acts_of(s, ActionType.ROLL)[0])
        assert s.winner == 1

    def test_win_target_is_fifteen(self):
        assert WINNING_POINTS == 15


class TestDeterminismAndCopy:
    def test_same_seed_same_scripted_game(self):
        def run(n=300):
            s = new_game(("A", "B"), seed=11)
            rng = random.Random(5)
            for _ in range(n):
                if s.is_terminal():
                    break
                apply_action(s, choose_action(s, legal_actions(s), rng), validate=False)
            return s
        a, b = run(), run()
        assert a.turn_number == b.turn_number
        assert a.phase == b.phase
        assert a.last_roll == b.last_roll
        assert a.buildings == b.buildings
        assert a.roads == b.roads
        for pa, pb in zip(a.players, b.players):
            assert pa.resources == pb.resources
            assert pa.dev_hand == pb.dev_hand

    def test_copy_is_independent(self):
        s = main_phase_game()
        c = s.copy()
        give(c.players[0], wood=5, brick=5)
        c.buildings.clear()
        assert s.buildings  # original untouched
        assert s.players[0].resources != c.players[0].resources

    def test_copy_preserves_rng_future(self):
        s = main_phase_game()
        c = s.copy()
        assert s.rng.random() == c.rng.random()  # same future stream

    def test_full_selfplay_terminates_with_a_real_winner(self):
        for seed in (3, 11):
            s = new_game(("A", "B"), seed=seed)
            rng = random.Random(seed)
            plies = 0
            while not s.is_terminal() and plies < 30_000:
                apply_action(s, choose_action(s, legal_actions(s), rng), validate=False)
                plies += 1
            assert s.winner is not None, f"seed {seed} did not terminate"
            assert s.total_vp(s.winner) >= WINNING_POINTS
            assert s.winner == s.current_player  # §12: won on their own turn
