import pytest
from app.models.game import Game, Player, Settlement, Road, PlayerType, GameStatus
from app.models.board import HexCoord, Vertex, Edge, Resource


class TestPlayer:
    """Test player functionality."""

    def test_player_creation(self):
        """Test creating a player."""
        player = Player(id=0, name="Player 1", player_type=PlayerType.HUMAN, color="#FF0000")
        assert player.name == "Player 1"
        assert player.points == 0
        assert player.resources[Resource.WOOD] == 0

    def test_add_resource(self):
        """Test adding resources to a player."""
        player = Player(id=0, name="Player 1", player_type=PlayerType.HUMAN, color="#FF0000")
        player.add_resource(Resource.WOOD, 3)
        assert player.resources[Resource.WOOD] == 3

    def test_remove_resource_success(self):
        """Test removing resources when player has enough."""
        player = Player(id=0, name="Player 1", player_type=PlayerType.HUMAN, color="#FF0000")
        player.add_resource(Resource.WOOD, 5)
        result = player.remove_resource(Resource.WOOD, 2)
        assert result is True
        assert player.resources[Resource.WOOD] == 3

    def test_remove_resource_failure(self):
        """Test removing resources when player doesn't have enough."""
        player = Player(id=0, name="Player 1", player_type=PlayerType.HUMAN, color="#FF0000")
        player.add_resource(Resource.WOOD, 1)
        result = player.remove_resource(Resource.WOOD, 5)
        assert result is False
        assert player.resources[Resource.WOOD] == 1

    def test_can_afford(self):
        """Test checking if player can afford something."""
        player = Player(id=0, name="Player 1", player_type=PlayerType.HUMAN, color="#FF0000")
        player.add_resource(Resource.WOOD, 2)
        player.add_resource(Resource.BRICK, 1)

        cost = {Resource.WOOD: 1, Resource.BRICK: 1}
        assert player.can_afford(cost) is True

        cost_unaffordable = {Resource.WOOD: 5}
        assert player.can_afford(cost_unaffordable) is False

    def test_pay_cost(self):
        """Test paying a cost in resources."""
        player = Player(id=0, name="Player 1", player_type=PlayerType.HUMAN, color="#FF0000")
        player.add_resource(Resource.WOOD, 2)
        player.add_resource(Resource.BRICK, 1)

        cost = {Resource.WOOD: 1, Resource.BRICK: 1}
        result = player.pay_cost(cost)
        assert result is True
        assert player.resources[Resource.WOOD] == 1
        assert player.resources[Resource.BRICK] == 0


class TestGame:
    """Test game functionality."""

    def test_game_creation(self):
        """Test creating a new game."""
        game = Game.create("game-1", "Alice")
        assert game.id == "game-1"
        assert len(game.players) == 2
        assert game.players[0].name == "Alice"
        assert game.players[1].name == "AI Opponent"
        assert game.board is not None
        assert len(game.board.hexes) == 19

    def test_current_player(self):
        """Test getting current player."""
        game = Game.create("game-1", "Alice")
        assert game.get_current_player().name == "Alice"
        assert game.get_current_player().id == 0

    def test_other_players(self):
        """Test getting other players."""
        game = Game.create("game-1", "Alice")
        others = game.get_other_players()
        assert len(others) == 1
        assert others[0].id == 1

    def test_next_turn(self):
        """Test advancing turns."""
        game = Game.create("game-1", "Alice")
        assert game.current_player_id == 0
        assert game.turn_number == 0

        game.next_turn()
        assert game.current_player_id == 1
        assert game.turn_number == 1

        game.next_turn()
        assert game.current_player_id == 0
        assert game.turn_number == 2

    # NOTE: Rules (placement, building, dice distribution, win check, costs) are
    # exercised against the single source of truth in tests/test_game_service.py.
    # Game itself is now a pure state container, so TestGame only covers state.

    def test_get_hexes_by_dice_number(self):
        """Test retrieving hexes by dice number."""
        game = Game.create("game-1", "Alice")
        hexes_6 = game.board.get_hexes_by_dice_number(6)
        assert len(hexes_6) > 0
        assert all(h.dice_number == 6 for h in hexes_6)


class TestSettlement:
    """Test settlement functionality."""

    def test_settlement_creation(self):
        """Test creating a settlement."""
        hexes = (HexCoord(0, 0), HexCoord(1, 0), HexCoord(0, 1))
        vertex = Vertex(hexes)
        settlement = Settlement(owner_id=0, vertex=vertex)
        assert settlement.owner_id == 0
        assert settlement.points == 1

    def test_settlement_hashing(self):
        """Test settlements can be used in sets."""
        hexes = (HexCoord(0, 0), HexCoord(1, 0), HexCoord(0, 1))
        vertex = Vertex(hexes)
        s1 = Settlement(owner_id=0, vertex=vertex)
        s2 = Settlement(owner_id=0, vertex=vertex)
        s_set = {s1, s2}
        assert len(s_set) == 1


class TestRoad:
    """Test road functionality."""

    def test_road_creation(self):
        """Test creating a road."""
        edge = Edge(HexCoord(0, 0), HexCoord(1, 0))
        road = Road(owner_id=0, edge=edge)
        assert road.owner_id == 0

    def test_road_hashing(self):
        """Test roads can be used in sets."""
        edge = Edge(HexCoord(0, 0), HexCoord(1, 0))
        r1 = Road(owner_id=0, edge=edge)
        r2 = Road(owner_id=0, edge=edge)
        r_set = {r1, r2}
        assert len(r_set) == 1
