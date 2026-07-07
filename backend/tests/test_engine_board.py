"""Board generation per CATAN_1V1_RULES.md §1–§2 (components, D5, D6)."""
from collections import Counter

from app.engine import DevCard, new_game
from app.engine.board_gen import coastal_vertices
from app.engine.state import DEV_DECK_COMPOSITION
from app.models.board import Resource

from tests.engine_test_utils import game


class TestBoardGeneration:
    def test_terrain_composition(self):
        s = game()
        counts = Counter(h.resource for h in s.board.hexes.values())
        assert counts[Resource.WOOD] == 4
        assert counts[Resource.SHEEP] == 4
        assert counts[Resource.WHEAT] == 4
        assert counts[Resource.BRICK] == 3
        assert counts[Resource.ORE] == 3
        assert counts[None] == 1  # exactly one desert

    def test_number_tokens(self):
        s = game()
        tokens = sorted(h.dice_number for h in s.board.hexes.values() if h.dice_number)
        assert tokens == [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

    def test_desert_has_no_number_and_hosts_robber(self):
        s = game()
        desert = next(h for h in s.board.hexes.values() if h.resource is None)
        assert desert.dice_number is None
        assert s.robber == desert.coord

    def test_red_numbers_never_adjacent(self):
        for seed in range(1, 20):
            s = game(seed)
            red = [h.coord for h in s.board.hexes.values() if h.dice_number in (6, 8)]
            red_set = set(red)
            for c in red:
                assert not any(nb in red_set for nb in c.neighbors()), f"seed {seed}"

    def test_ports_composition_and_placement(self):
        s = game()
        assert len(s.ports) == 9
        types = Counter(s.ports.values())
        assert types[None] == 4  # generic 3:1
        for r in Resource:
            assert types[r] == 1  # one 2:1 port per resource
        coast = set(coastal_vertices(s.board))
        assert all(v in coast for v in s.ports)

    def test_dev_deck_composition(self):
        s = game()
        assert len(s.dev_deck) == 25
        counts = Counter(s.dev_deck)
        assert counts[DevCard.KNIGHT] == 14
        assert counts[DevCard.VICTORY_POINT] == 5
        assert counts[DevCard.ROAD_BUILDING] == 2
        assert counts[DevCard.YEAR_OF_PLENTY] == 2
        assert counts[DevCard.MONOPOLY] == 2
        assert sorted(counts.values()) != []  # shuffled deck retains composition

    def test_same_seed_same_board(self):
        a, b = game(7), game(7)
        assert [(h.coord, h.resource, h.dice_number) for h in a.board.hexes.values()] == \
               [(h.coord, h.resource, h.dice_number) for h in b.board.hexes.values()]
        assert a.dev_deck == b.dev_deck
        assert a.ports == b.ports

    def test_different_seeds_differ(self):
        layouts = {
            tuple((h.coord.q, h.coord.r, h.resource, h.dice_number)
                  for h in game(s).board.hexes.values())
            for s in range(5)
        }
        assert len(layouts) > 1
