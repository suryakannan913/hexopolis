"""Rolling a 7 (§6): discards (D2 threshold), robber movement incl. the
friendly-robber rule (§6.1/D9), and stealing."""
from app.engine import ActionType, Phase, SETTLEMENT, apply_action, legal_actions
from app.engine.rules import _robber_destinations
from app.models.board import Resource

from tests.engine_test_utils import acts_of, game, give, main_phase_game, run_setup, seed_rolling


class TestDiscards:
    def test_discard_only_above_nine_cards(self):
        s = run_setup(game())
        for r in Resource:
            s.players[0].resources[r] = 2   # 10 cards -> must discard 5
            s.players[1].resources[r] = 0
        s.players[1].resources[Resource.WOOD] = 9  # exactly 9 -> safe
        s.rng = seed_rolling(7)
        apply_action(s, acts_of(s, ActionType.ROLL)[0])
        assert s.phase == Phase.DISCARD
        assert s.discard_quota == [5, 0]

    def test_discard_actions_and_flow_to_robber(self):
        s = run_setup(game())
        for r in Resource:
            s.players[0].resources[r] = 2
            s.players[1].resources[r] = 0
        s.rng = seed_rolling(7)
        apply_action(s, acts_of(s, ActionType.ROLL)[0])
        bank_before = sum(s.bank.values())
        while s.phase == Phase.DISCARD:
            acts = legal_actions(s)
            assert all(a.type == ActionType.DISCARD and a.player == 0 for a in acts)
            apply_action(s, acts[0])
        assert s.players[0].hand_size() == 5          # kept half (floor)
        assert sum(s.bank.values()) == bank_before + 5  # discards go to the bank
        assert s.phase == Phase.MOVE_ROBBER
        assert s.actor() == 0  # the roller moves the robber


class TestFriendlyRobber:
    def test_low_vp_opponent_hexes_are_protected(self):
        s = main_phase_game()  # both players: 2 settlements -> visible VP 2
        assert s.visible_vp(1) == 2
        opp_hexes = {
            h.coord for v, (o, _) in s.buildings.items() if o == 1
            for h in s.board.get_hexes_for_vertex(v)
        }
        dests = set(_robber_destinations(s, mover=0))
        assert opp_hexes.isdisjoint(dests)
        assert dests  # own/empty hexes always remain (no deadlock)
        assert s.robber not in dests  # must move to a different hex

    def test_protection_lifts_above_two_visible_vp(self):
        s = main_phase_game()
        # Give the opponent a third settlement -> visible VP 3
        free = next(
            v for v in s.board.get_all_vertices()
            if v not in s.buildings
            and all(len(set(v.hex_coords) & set(w.hex_coords)) != 2 for w in s.buildings)
        )
        s.buildings[free] = (1, SETTLEMENT)
        assert s.visible_vp(1) == 3
        opp_hexes = {
            h.coord for v, (o, _) in s.buildings.items() if o == 1
            for h in s.board.get_hexes_for_vertex(v)
        }
        dests = set(_robber_destinations(s, mover=0))
        assert opp_hexes & dests  # now targetable

    def test_own_buildings_never_protect(self):
        s = main_phase_game()
        own_hexes = {
            h.coord for v, (o, _) in s.buildings.items() if o == 0
            for h in s.board.get_hexes_for_vertex(v)
        }
        opp_hexes = {
            h.coord for v, (o, _) in s.buildings.items() if o == 1
            for h in s.board.get_hexes_for_vertex(v)
        }
        dests = set(_robber_destinations(s, mover=0))
        assert (own_hexes - opp_hexes) <= dests | {s.robber}


class TestStealing:
    def test_moving_next_to_opponent_steals_one_random_card(self):
        s = main_phase_game()
        s.players[1].resources = {r: 0 for r in Resource}
        s.players[1].resources[Resource.WOOD] = 3
        # opponent must be above the friendly threshold to be a legal target
        free = next(
            v for v in s.board.get_all_vertices()
            if v not in s.buildings
            and all(len(set(v.hex_coords) & set(w.hex_coords)) != 2 for w in s.buildings)
        )
        s.buildings[free] = (1, SETTLEMENT)
        s.phase = Phase.MOVE_ROBBER
        target = next(
            h.coord for h in s.board.get_hexes_for_vertex(free)
            if s.board.hex_exists(h.coord) and h.coord != s.robber
        )
        act = next(a for a in legal_actions(s) if a.value == target)
        p0_wood = s.players[0].resources[Resource.WOOD]
        apply_action(s, act)
        assert s.players[0].resources[Resource.WOOD] == p0_wood + 1  # only wood to steal
        assert s.players[1].resources[Resource.WOOD] == 2
        assert s.phase == Phase.MAIN

    def test_no_building_no_steal(self):
        s = main_phase_game()
        s.phase = Phase.MOVE_ROBBER
        opp_vertices = {v for v, (o, _) in s.buildings.items() if o == 1}
        empty_dest = next(
            c for c in _robber_destinations(s, mover=0)
            if not any(v in opp_vertices for v in s.board.get_vertices_for_hex(c))
        )
        hands = [p.hand_size() for p in s.players]
        apply_action(s, next(a for a in legal_actions(s) if a.value == empty_dest))
        assert [p.hand_size() for p in s.players] == hands
