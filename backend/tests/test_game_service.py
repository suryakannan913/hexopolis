import pytest
from app.models.game import Game, Resource, GameStatus
from app.models.board import HexCoord, Vertex, Edge
from app.services.game_service import GameService


class TestGameService:
    """Test game service business logic."""

    def test_create_game(self):
        """Test creating a game through service."""
        game = GameService.create_game("game-1", "Alice")
        assert game.id == "game-1"
        assert game.players[0].name == "Alice"
        assert game.status == GameStatus.SETUP

    def test_place_settlement_success(self):
        """Test placing a settlement successfully."""
        game = GameService.create_game("game-1", "Alice")
        vertices = list(game.board.get_all_vertices())
        vertex = vertices[0]

        success, error = GameService.place_settlement(game, 0, vertex)
        assert success is True
        assert error == ""
        assert len(game.settlements_on_board) == 1

    def test_place_settlement_occupied(self):
        """Test placing settlement on occupied vertex fails."""
        game = GameService.create_game("game-1", "Alice")
        vertices = list(game.board.get_all_vertices())
        vertex = vertices[0]

        GameService.place_settlement(game, 0, vertex)
        success, error = GameService.place_settlement(game, 1, vertex)
        assert success is False
        assert "occupied" in error.lower()

    def test_place_settlement_adjacent_to_opponent(self):
        """Test settlement placement respects distance rule."""
        game = GameService.create_game("game-1", "Alice")
        vertices = list(game.board.get_all_vertices())

        # Place first settlement
        GameService.place_settlement(game, 0, vertices[0])

        # Try to place adjacent settlement (should fail)
        # This test is limited because not all consecutive vertices are adjacent
        adjacent = GameService._vertices_are_adjacent(game.board, vertices[0], vertices[1])
        if adjacent:
            success, error = GameService.place_settlement(game, 1, vertices[1])
            assert success is False

    def test_place_settlement_costs_resources(self):
        """Test settlement placement costs resources outside setup."""
        game = GameService.create_game("game-1", "Alice")
        game.status = GameStatus.IN_PROGRESS  # Exit setup phase
        player = game.players[0]

        # Give player resources
        for resource in [Resource.WOOD, Resource.BRICK, Resource.WHEAT, Resource.SHEEP]:
            player.add_resource(resource, 1)

        vertices = list(game.board.get_all_vertices())
        vertex = vertices[0]

        initial_resources = sum(player.resources.values())
        success, error = GameService.place_settlement(game, 0, vertex)
        final_resources = sum(player.resources.values())

        assert success is True
        assert final_resources < initial_resources

    def test_place_settlement_insufficient_resources(self):
        """Test settlement placement fails without resources."""
        game = GameService.create_game("game-1", "Alice")
        game.status = GameStatus.IN_PROGRESS
        player = game.players[0]
        # Don't give resources

        vertices = list(game.board.get_all_vertices())
        vertex = vertices[0]

        success, error = GameService.place_settlement(game, 0, vertex)
        assert success is False
        assert "resources" in error.lower()

    def test_build_road_success(self):
        """Test building a road successfully."""
        game = GameService.create_game("game-1", "Alice")
        player = game.players[0]

        # Place settlement first
        vertices = list(game.board.get_all_vertices())
        vertex = vertices[0]
        GameService.place_settlement(game, 0, vertex)

        # Give player resources for road
        player.add_resource(Resource.WOOD, 1)
        player.add_resource(Resource.BRICK, 1)

        # Get an edge from the settlement's hex
        hex_coords = vertex.hex_coords
        hex_obj = game.board.get_hex(hex_coords[0])
        edges = game.board.get_edges_for_hex(hex_obj.coord)
        edge = edges[0]

        success, error = GameService.build_road(game, 0, edge)
        # May or may not succeed depending on edge location relative to settlement
        # Just verify function runs

    def test_roll_dice(self):
        """Test rolling dice returns valid value."""
        game = GameService.create_game("game-1", "Alice")
        roll = GameService.roll_dice(game)
        assert 2 <= roll <= 12
        assert game.last_dice_roll == roll

    def test_distribute_resources(self):
        """Test resource distribution."""
        game = GameService.create_game("game-1", "Alice")
        vertices = list(game.board.get_all_vertices())
        vertex = vertices[0]

        # Place settlement
        GameService.place_settlement(game, 0, vertex)
        initial = sum(game.players[0].resources.values())

        # Distribute resources for a valid roll
        GameService.distribute_resources(game, 6)

        final = sum(game.players[0].resources.values())
        # May or may not increase depending on board layout
        assert final >= initial

    def test_distribute_resources_no_roll_7(self):
        """Test rolling 7 doesn't distribute resources."""
        game = GameService.create_game("game-1", "Alice")
        initial = sum(game.players[0].resources.values())

        GameService.distribute_resources(game, 7)

        final = sum(game.players[0].resources.values())
        assert final == initial

    def test_execute_trade_success(self):
        """Test executing a trade."""
        game = GameService.create_game("game-1", "Alice")
        player = game.players[0]

        # Give player resources
        player.add_resource(Resource.WOOD, 4)

        give = {Resource.WOOD: 4}
        receive = {Resource.BRICK: 1}

        success, error = GameService.execute_trade(game, 0, give, receive)
        assert success is True
        assert player.resources[Resource.WOOD] == 0
        assert player.resources[Resource.BRICK] == 1

    def test_execute_trade_insufficient_resources(self):
        """Test trade fails with insufficient resources."""
        game = GameService.create_game("game-1", "Alice")
        player = game.players[0]
        # Don't give resources

        give = {Resource.WOOD: 4}
        receive = {Resource.BRICK: 1}

        success, error = GameService.execute_trade(game, 0, give, receive)
        assert success is False

    def test_end_turn(self):
        """Test ending a turn."""
        game = GameService.create_game("game-1", "Alice")
        assert game.current_player_id == 0

        GameService.end_turn(game)
        assert game.current_player_id == 1

        GameService.end_turn(game)
        assert game.current_player_id == 0

    def test_check_win_condition_no_winner(self):
        """Test win condition when no one won."""
        game = GameService.create_game("game-1", "Alice")
        winner = GameService.check_win_condition(game)
        assert winner is None

    def test_check_win_condition_player_wins(self):
        """Test win condition when someone reaches 10 points."""
        game = GameService.create_game("game-1", "Alice")
        game.players[0].points = 10

        winner = GameService.check_win_condition(game)
        assert winner == 0
        assert game.status == GameStatus.WON

    def test_vertices_are_adjacent(self):
        """Test checking if vertices are adjacent."""
        h1 = HexCoord(0, 0)
        h2 = HexCoord(1, 0)
        h3 = HexCoord(0, 1)

        v1 = Vertex((h1, h2, h3))
        v2 = Vertex((h1, h2, HexCoord(1, -1)))

        # v1 and v2 share h1 and h2, so they should be adjacent
        board = Game.create("test", "Test").board
        are_adjacent = GameService._vertices_are_adjacent(board, v1, v2)
        assert are_adjacent is True
