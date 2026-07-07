"""Opening placement per §3: snake draft, road per settlement, round-2 resources."""
from app.engine import ActionType, Phase, apply_action, legal_actions
from app.models.board import Resource

from tests.engine_test_utils import game, run_setup


class TestSetupPhase:
    def test_snake_draft_order(self):
        s = game()
        actors = []
        while s.phase in (Phase.SETUP_SETTLEMENT, Phase.SETUP_ROAD):
            if s.phase == Phase.SETUP_SETTLEMENT:
                actors.append(s.actor())
            apply_action(s, legal_actions(s)[0], validate=False)
        assert actors == [0, 1, 1, 0]  # P1, P2, P2, P1

    def test_all_54_vertices_open_initially(self):
        s = game()
        acts = legal_actions(s)
        assert len(acts) == 54
        assert all(a.type == ActionType.BUILD_SETTLEMENT for a in acts)

    def test_setup_road_must_touch_new_settlement(self):
        s = game()
        settle = legal_actions(s)[0]
        apply_action(s, settle)
        assert s.phase == Phase.SETUP_ROAD
        road_acts = legal_actions(s)
        assert road_acts and all(a.type == ActionType.BUILD_ROAD for a in road_acts)
        endpoints_ok = [
            settle.value in s.board.get_edge_endpoints(a.value) for a in road_acts
        ]
        assert all(endpoints_ok)

    def test_distance_rule_applies_during_setup(self):
        s = game()
        settle = legal_actions(s)[0]
        apply_action(s, settle)
        apply_action(s, legal_actions(s)[0])  # P0's road
        # P1 may not place on or adjacent to P0's settlement
        for a in legal_actions(s):
            v = a.value
            assert v != settle.value
            assert len(set(v.hex_coords) & set(settle.value.hex_coords)) != 2

    def test_second_settlement_grants_resources_first_does_not(self):
        s = game()
        second_settlements = {}
        while s.phase in (Phase.SETUP_SETTLEMENT, Phase.SETUP_ROAD):
            act = legal_actions(s)[0]
            if s.phase == Phase.SETUP_SETTLEMENT and s.setup_index in (2, 3):
                second_settlements[act.player] = act.value
            hands_before = [p.hand_size() for p in s.players]
            apply_action(s, act, validate=False)
            if s.setup_index in (0, 1) or (act.type == ActionType.BUILD_ROAD):
                # first-round placements and roads grant nothing
                assert [p.hand_size() for p in s.players] == hands_before

        for pid, v in second_settlements.items():
            expected = sum(
                1 for h in s.board.get_hexes_for_vertex(v) if h.resource is not None
            )
            assert s.players[pid].hand_size() == expected
            # granted cards came out of the bank
        total_granted = sum(p.hand_size() for p in s.players)
        assert sum(s.bank.values()) == 19 * 5 - total_granted

    def test_setup_consumes_supply_and_enters_main(self):
        s = run_setup(game())
        assert s.phase == Phase.MAIN
        assert s.current_player == 0 and s.turn_number == 1
        for p in s.players:
            assert p.settlements_left == 3   # 5 - 2
            assert p.roads_left == 13        # 15 - 2
