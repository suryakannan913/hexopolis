"""Building (§8), development cards (§10), maritime trading (§7 / D1)."""
from app.engine import (
    ActionType,
    CITY,
    DevCard,
    Phase,
    SETTLEMENT,
    apply_action,
    legal_actions,
)
from app.engine.rules import trade_rate
from app.engine.state import CITY_COST, DEV_CARD_COST, ROAD_COST, SETTLEMENT_COST
from app.models.board import Resource

from tests.engine_test_utils import acts_of, give, main_phase_game


class TestBuilding:
    def test_road_costs_and_pays_bank(self):
        s = main_phase_game()
        p = s.players[0]
        for r in Resource:
            p.resources[r] = 0
        give(p, wood=1, brick=1)
        bank_wood = s.bank[Resource.WOOD]
        act = acts_of(s, ActionType.BUILD_ROAD)[0]
        apply_action(s, act)
        assert p.resources[Resource.WOOD] == 0 and p.resources[Resource.BRICK] == 0
        assert s.bank[Resource.WOOD] == bank_wood + 1
        assert s.roads[act.value] == 0
        assert p.roads_left == 12  # 13 after setup, minus this one

    def test_road_requires_connection(self):
        s = main_phase_game()
        give(s.players[0], wood=1, brick=1)
        own_road_or_building_vertices = set()
        for e, o in s.roads.items():
            if o == 0:
                own_road_or_building_vertices |= set(s.board.get_edge_endpoints(e))
        for v, (o, _) in s.buildings.items():
            if o == 0:
                own_road_or_building_vertices.add(v)
        for a in acts_of(s, ActionType.BUILD_ROAD):
            endpoints = set(s.board.get_edge_endpoints(a.value))
            assert endpoints & own_road_or_building_vertices

    def test_settlement_requires_own_road_and_distance(self):
        s = main_phase_game()
        give(s.players[0], wood=1, brick=1, sheep=1, wheat=1)
        for a in acts_of(s, ActionType.BUILD_SETTLEMENT):
            v = a.value
            assert any(s.roads.get(e) == 0 for e in s.board.get_edges_for_vertex(v))
            for w in s.buildings:
                assert len(set(v.hex_coords) & set(w.hex_coords)) != 2

    def test_no_settlement_without_resources(self):
        s = main_phase_game()
        for r in Resource:
            s.players[0].resources[r] = 0
        assert not acts_of(s, ActionType.BUILD_SETTLEMENT)

    def test_city_upgrades_settlement_and_returns_piece(self):
        s = main_phase_game()
        p = s.players[0]
        give(p, ore=3, wheat=2)
        v = s.settlements_of(0)[0]
        settlements_left = p.settlements_left
        apply_action(s, next(a for a in acts_of(s, ActionType.BUILD_CITY) if a.value == v))
        assert s.buildings[v] == (0, CITY)
        assert p.settlements_left == settlements_left + 1
        assert p.cities_left == 3
        assert s.visible_vp(0) == 3  # 1 settlement + 1 city

    def test_supply_limits_block_building(self):
        s = main_phase_game()
        p = s.players[0]
        give(p, wood=5, brick=5, sheep=5, wheat=5, ore=5)
        p.roads_left = 0
        p.settlements_left = 0
        p.cities_left = 0
        types = {a.type for a in legal_actions(s)}
        assert ActionType.BUILD_ROAD not in types
        assert ActionType.BUILD_SETTLEMENT not in types
        assert ActionType.BUILD_CITY not in types


class TestDevCards:
    def test_buy_draws_from_deck_and_blocks_same_turn_play(self):
        s = main_phase_game()
        p = s.players[0]
        give(p, ore=1, sheep=1, wheat=1)
        s.dev_deck = [DevCard.KNIGHT]
        apply_action(s, acts_of(s, ActionType.BUY_DEV_CARD)[0])
        assert p.dev_hand[DevCard.KNIGHT] == 1
        assert not s.dev_deck
        assert not acts_of(s, ActionType.PLAY_KNIGHT)  # §10: not the turn it was bought

    def test_bought_card_playable_next_turn(self):
        s = main_phase_game()
        p = s.players[0]
        give(p, ore=1, sheep=1, wheat=1)
        s.dev_deck = [DevCard.KNIGHT]
        apply_action(s, acts_of(s, ActionType.BUY_DEV_CARD)[0])
        apply_action(s, acts_of(s, ActionType.END_TURN)[0])
        s.current_player = 0  # test shortcut back to P0's turn
        s.has_rolled = True
        assert acts_of(s, ActionType.PLAY_KNIGHT)

    def test_one_dev_card_per_turn(self):
        s = main_phase_game()
        p = s.players[0]
        p.dev_hand[DevCard.KNIGHT] = 1
        p.dev_hand[DevCard.MONOPOLY] = 1
        assert acts_of(s, ActionType.PLAY_KNIGHT) and acts_of(s, ActionType.PLAY_MONOPOLY)
        apply_action(s, acts_of(s, ActionType.PLAY_MONOPOLY)[0])
        assert not acts_of(s, ActionType.PLAY_KNIGHT)

    def test_knight_moves_robber_without_discards(self):
        s = main_phase_game()
        p = s.players[0]
        p.dev_hand[DevCard.KNIGHT] = 1
        for r in Resource:  # a huge hand must NOT trigger discards on a knight
            p.resources[r] = 4
        apply_action(s, acts_of(s, ActionType.PLAY_KNIGHT)[0])
        assert s.phase == Phase.MOVE_ROBBER
        assert p.knights_played == 1
        assert s.discard_quota == [0, 0]

    def test_knight_playable_before_roll_and_roll_still_required(self):
        s = main_phase_game(rolled=False)
        s.players[0].dev_hand[DevCard.KNIGHT] = 1
        assert acts_of(s, ActionType.PLAY_KNIGHT)  # §4: dev card allowed pre-roll
        apply_action(s, acts_of(s, ActionType.PLAY_KNIGHT)[0])
        apply_action(s, legal_actions(s)[0])  # move the robber somewhere legal
        assert s.phase == Phase.MAIN and not s.has_rolled
        assert acts_of(s, ActionType.ROLL)

    def test_largest_army_first_to_three_then_strictly_more(self):
        s = main_phase_game()
        s.players[0].knights_played = 2
        s.players[0].dev_hand[DevCard.KNIGHT] = 1
        apply_action(s, acts_of(s, ActionType.PLAY_KNIGHT)[0])
        assert s.largest_army_owner == 0
        assert s.visible_vp(0) == 4  # 2 settlements + LA
        # opponent ties at 3: no transfer; at 4: transfer
        from app.engine.rules import _maintain_largest_army
        s.players[1].knights_played = 3
        _maintain_largest_army(s, 1)
        assert s.largest_army_owner == 0
        s.players[1].knights_played = 4
        _maintain_largest_army(s, 1)
        assert s.largest_army_owner == 1

    def test_road_building_places_two_free_roads(self):
        s = main_phase_game()
        p = s.players[0]
        p.dev_hand[DevCard.ROAD_BUILDING] = 1
        for r in Resource:
            p.resources[r] = 0
        roads_before = len(s.roads_of(0))
        apply_action(s, acts_of(s, ActionType.PLAY_ROAD_BUILDING)[0])
        assert s.free_roads_pending == 2
        # only free road placements are on offer
        assert {a.type for a in legal_actions(s)} == {ActionType.BUILD_ROAD}
        apply_action(s, legal_actions(s)[0])
        apply_action(s, legal_actions(s)[0])
        assert s.free_roads_pending == 0
        assert len(s.roads_of(0)) == roads_before + 2
        assert p.hand_size() == 0  # free: no resources spent

    def test_road_building_capped_by_supply(self):
        s = main_phase_game()
        p = s.players[0]
        p.dev_hand[DevCard.ROAD_BUILDING] = 1
        p.roads_left = 1
        apply_action(s, acts_of(s, ActionType.PLAY_ROAD_BUILDING)[0])
        assert s.free_roads_pending == 1

    def test_year_of_plenty_takes_two_from_bank(self):
        s = main_phase_game()
        p = s.players[0]
        p.dev_hand[DevCard.YEAR_OF_PLENTY] = 1
        act = next(a for a in acts_of(s, ActionType.PLAY_YEAR_OF_PLENTY)
                   if a.value == (Resource.ORE, Resource.ORE))
        ore_before, bank_before = p.resources[Resource.ORE], s.bank[Resource.ORE]
        apply_action(s, act)
        assert p.resources[Resource.ORE] == ore_before + 2
        assert s.bank[Resource.ORE] == bank_before - 2

    def test_year_of_plenty_limited_by_bank(self):
        s = main_phase_game()
        p = s.players[0]
        p.dev_hand[DevCard.YEAR_OF_PLENTY] = 1
        for r in Resource:
            s.bank[r] = 0
        s.bank[Resource.WOOD] = 1  # only one card left anywhere
        vals = [a.value for a in acts_of(s, ActionType.PLAY_YEAR_OF_PLENTY)]
        assert vals == [(Resource.WOOD,)]  # §10: take what is available

    def test_monopoly_takes_all_of_named_resource(self):
        s = main_phase_game()
        p, opp = s.players[0], s.players[1]
        p.dev_hand[DevCard.MONOPOLY] = 1
        opp.resources[Resource.SHEEP] = 4
        mine_before = p.resources[Resource.SHEEP]
        bank_before = s.bank[Resource.SHEEP]
        act = next(a for a in acts_of(s, ActionType.PLAY_MONOPOLY)
                   if a.value == Resource.SHEEP)
        apply_action(s, act)
        assert p.resources[Resource.SHEEP] == mine_before + 4
        assert opp.resources[Resource.SHEEP] == 0
        assert s.bank[Resource.SHEEP] == bank_before  # hand-to-hand, not via bank

    def test_victory_point_cards_hidden_from_visible_vp(self):
        s = main_phase_game()
        s.players[0].dev_hand[DevCard.VICTORY_POINT] = 2
        assert s.visible_vp(0) == 2       # settlements only
        assert s.total_vp(0) == 4         # + hidden VP cards
        # VP cards are never "played" — no such action type exists
        assert not [a for a in legal_actions(s) if "victory" in a.type.value]


class TestMaritimeTrade:
    def test_default_rate_is_four_to_one(self):
        s = main_phase_game()
        p = s.players[0]
        for r in Resource:
            p.resources[r] = 0
        s.buildings = {v: b for v, b in s.buildings.items() if v not in s.ports}
        give(p, wood=3)
        assert not acts_of(s, ActionType.MARITIME_TRADE)
        give(p, wood=1)  # now 4
        trades = acts_of(s, ActionType.MARITIME_TRADE)
        assert trades and all(a.value[0] == Resource.WOOD for a in trades)
        assert all(a.value[1] != Resource.WOOD for a in trades)  # never same back

    def test_trade_moves_resources_through_bank(self):
        s = main_phase_game()
        p = s.players[0]
        for r in Resource:
            p.resources[r] = 0
        give(p, wood=4)
        act = next(a for a in acts_of(s, ActionType.MARITIME_TRADE)
                   if a.value == (Resource.WOOD, Resource.ORE))
        bank_wood, bank_ore = s.bank[Resource.WOOD], s.bank[Resource.ORE]
        apply_action(s, act)
        assert p.resources[Resource.WOOD] == 0 and p.resources[Resource.ORE] == 1
        assert s.bank[Resource.WOOD] == bank_wood + 4
        assert s.bank[Resource.ORE] == bank_ore - 1

    def test_generic_port_gives_three_to_one(self):
        s = main_phase_game()
        v = next(v for v, t in s.ports.items() if t is None)
        s.buildings[v] = (0, SETTLEMENT)
        assert trade_rate(s, 0, Resource.WOOD) == 3

    def test_specific_port_gives_two_to_one_for_its_resource_only(self):
        s = main_phase_game()
        v = next(v for v, t in s.ports.items() if t == Resource.WOOD)
        s.buildings[v] = (0, SETTLEMENT)
        assert trade_rate(s, 0, Resource.WOOD) == 2
        assert trade_rate(s, 0, Resource.ORE) == 4  # unaffected

    def test_cannot_receive_resource_bank_is_out_of(self):
        s = main_phase_game()
        p = s.players[0]
        for r in Resource:
            p.resources[r] = 0
        give(p, wood=4)
        s.bank[Resource.BRICK] = 0
        assert not [a for a in acts_of(s, ActionType.MARITIME_TRADE)
                    if a.value[1] == Resource.BRICK]
