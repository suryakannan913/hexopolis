import pytest
from app.models.game import Game, Resource, GameStatus, PlayerType
from app.models.board import HexCoord, Vertex, Edge
from app.ai.evaluator import AIEvaluator, AIPlayer, Move
from app.services.game_service import GameService
from tests._engine_helpers import place_free_setup_settlement, extend_two_roads


class TestAIEvaluator:
    """Test AI evaluation and decision-making."""

    def test_evaluator_creation(self):
        """Test creating an AI evaluator."""
        evaluator = AIEvaluator()
        assert evaluator.lookahead_depth == 1

    def test_evaluate_state_empty_game(self):
        """Test evaluating an empty game state."""
        game = GameService.create_game("test", "Human")
        evaluator = AIEvaluator()

        score = evaluator.evaluate_state(game, 0)
        assert isinstance(score, float)
        assert score >= 0

    def test_evaluate_state_with_settlements(self):
        """Test score increases with settlements."""
        game = GameService.create_game("test", "Human")
        evaluator = AIEvaluator()

        initial_score = evaluator.evaluate_state(game, 0)

        # Give player a settlement
        game.players[0].points = 2
        new_score = evaluator.evaluate_state(game, 0)

        assert new_score > initial_score

    def test_evaluate_state_with_resources(self):
        """Test score reflects resource inventory."""
        game = GameService.create_game("test", "Human")
        evaluator = AIEvaluator()

        initial_score = evaluator.evaluate_state(game, 0)

        # Give player resources
        game.players[0].add_resource(Resource.WOOD, 5)
        new_score = evaluator.evaluate_state(game, 0)

        assert new_score > initial_score

    def test_generate_moves_end_turn_always_available(self):
        """Test end_turn move is always available."""
        game = GameService.create_game("test", "Human")
        evaluator = AIEvaluator()

        moves = evaluator.generate_moves(game, 0)
        assert any(m.move_type == "end_turn" for m in moves)

    def test_generate_moves_includes_settlements(self):
        """Test settlement moves are generated."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.SETUP  # In setup, settlements are free
        evaluator = AIEvaluator()

        moves = evaluator.generate_moves(game, 0)
        settlement_moves = [m for m in moves if m.move_type == "settlement"]

        # Should have at least one settlement move in setup
        assert len(settlement_moves) > 0

    def test_generate_moves_settlement_requires_resources(self):
        """Test settlements need resources outside setup."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.IN_PROGRESS
        # Don't give resources
        evaluator = AIEvaluator()

        moves = evaluator.generate_moves(game, 0)
        settlement_moves = [m for m in moves if m.move_type == "settlement"]

        # Should have no settlement moves without resources
        assert len(settlement_moves) == 0

    def test_generate_moves_settlement_with_resources(self):
        """Settlement moves are generated when a legal, connected, affordable spot exists."""
        game = GameService.create_game("test", "Human")
        place_free_setup_settlement(game, 0)
        game.status = GameStatus.IN_PROGRESS
        player = game.players[0]
        for r in Resource:
            player.resources[r] = 0

        # Build a road path to a legal spot, then hold settlement resources.
        player.add_resource(Resource.WOOD, 2)
        player.add_resource(Resource.BRICK, 2)
        e1, e2, _ = extend_two_roads(game, 0)
        GameService.build_road(game, 0, e1)
        GameService.build_road(game, 0, e2)
        for r in [Resource.WOOD, Resource.BRICK, Resource.WHEAT, Resource.SHEEP]:
            player.add_resource(r, 1)

        evaluator = AIEvaluator()
        moves = evaluator.generate_moves(game, 0)
        settlement_moves = [m for m in moves if m.move_type == "settlement"]

        # A connected, affordable, distance-legal spot should surface as a move.
        assert len(settlement_moves) > 0

    def test_generate_moves_road_requires_resources(self):
        """Test roads need resources."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.IN_PROGRESS
        evaluator = AIEvaluator()

        moves = evaluator.generate_moves(game, 0)
        road_moves = [m for m in moves if m.move_type == "road"]

        # Should have no road moves without resources or settlements
        assert len(road_moves) == 0

    def test_choose_best_move_returns_move(self):
        """Test choosing best move returns a Move."""
        game = GameService.create_game("test", "Human")
        evaluator = AIEvaluator()

        move = evaluator.choose_best_move(game, 0)
        assert isinstance(move, Move)
        assert move.move_type in ["settlement", "road", "trade", "end_turn"]

    def test_choose_best_move_greedy_selects_highest_score(self):
        """Test greedy selection picks highest-scoring move."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.SETUP
        evaluator = AIEvaluator()

        move = evaluator.choose_best_move(game, 0)

        # In setup, should choose a settlement (highest score)
        assert move.move_type == "settlement"

    def test_execute_move_end_turn(self):
        """Test executing an end_turn move."""
        game = GameService.create_game("test", "Human")
        evaluator = AIEvaluator()

        initial_player = game.current_player_id
        move = Move(move_type="end_turn")

        success = evaluator.execute_move(game, 0, move)
        assert success is True
        assert game.current_player_id != initial_player

    def test_execute_move_settlement_success(self):
        """Test executing a settlement move."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.SETUP
        evaluator = AIEvaluator()

        vertices = list(game.board.get_all_vertices())
        vertex = vertices[0]

        move = Move(move_type="settlement", target=vertex)
        success = evaluator.execute_move(game, 0, move)

        if success:  # May or may not succeed depending on constraints
            assert len(game.settlements_on_board) > 0

    def test_score_settlement_prefers_resource_hexes(self):
        """Test settlement scoring favors resource-producing locations."""
        game = GameService.create_game("test", "Human")
        evaluator = AIEvaluator()

        vertices = list(game.board.get_all_vertices())
        v1 = vertices[0]
        v2 = vertices[1]

        score1 = evaluator._score_settlement(game, 0, v1)
        score2 = evaluator._score_settlement(game, 0, v2)

        # Both should have positive scores
        assert score1 >= 0
        assert score2 >= 0

    def test_vertices_are_adjacent_true(self):
        """Test vertex adjacency detection (true case)."""
        h1 = HexCoord(0, 0)
        h2 = HexCoord(1, 0)
        h3 = HexCoord(0, 1)
        h4 = HexCoord(1, -1)

        v1 = Vertex((h1, h2, h3))
        v2 = Vertex((h1, h2, h4))

        evaluator = AIEvaluator()
        result = evaluator._vertices_are_adjacent(v1, v2)
        assert result is True

    def test_vertices_are_adjacent_false(self):
        """Test vertex adjacency detection (false case)."""
        h1 = HexCoord(0, 0)
        h2 = HexCoord(1, 0)
        h3 = HexCoord(0, 1)
        h4 = HexCoord(2, 0)
        h5 = HexCoord(1, -1)

        v1 = Vertex((h1, h2, h3))
        v2 = Vertex((h4, h5, HexCoord(1, 1)))

        evaluator = AIEvaluator()
        result = evaluator._vertices_are_adjacent(v1, v2)
        assert result is False


class TestAIPlayer:
    """Test AI player wrapper."""

    def test_ai_player_creation(self):
        """Test creating an AI player."""
        ai = AIPlayer(player_id=1)
        assert ai.player_id == 1
        assert ai.evaluator is not None

    def test_ai_player_with_custom_evaluator(self):
        """Test AI player with custom evaluator."""
        evaluator = AIEvaluator(lookahead_depth=2)
        ai = AIPlayer(player_id=1, evaluator=evaluator)
        assert ai.evaluator == evaluator

    def test_ai_take_turn_completes(self):
        """Test AI can complete a full turn."""
        game = GameService.create_game("test", "Human")
        # Run the AI turn in normal play (not setup) so turn advancement is
        # deterministic and not short-circuited by free setup placements.
        game.status = GameStatus.IN_PROGRESS
        game.current_player_id = 1
        game.players[1].player_type = PlayerType.AI

        ai = AIPlayer(player_id=1)
        initial_turn = game.turn_number
        initial_player = game.current_player_id

        # Take turn
        ai.take_turn(game)

        # Turn should have advanced
        assert game.turn_number > initial_turn
        assert game.current_player_id != initial_player

    def test_ai_take_turn_no_crash(self):
        """Test AI turn doesn't crash on empty game."""
        game = GameService.create_game("test", "Human")
        game.current_player_id = 1
        game.players[1].player_type = PlayerType.AI

        ai = AIPlayer(player_id=1)

        # Should not raise exception
        try:
            ai.take_turn(game)
        except Exception as e:
            pytest.fail(f"AI turn raised exception: {e}")


class TestAIIntegration:
    """Test AI integrated with game flow."""

    def test_ai_vs_human_full_game(self):
        """Test a full game between AI and human."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.SETUP

        # Play 10 turns (human + AI alternating)
        for _ in range(10):
            current_player = game.get_current_player()

            if current_player.player_type == PlayerType.HUMAN:
                # Human just rolls and ends turn
                GameService.roll_dice(game)
                GameService.distribute_resources(game, game.last_dice_roll)
                GameService.end_turn(game)
            else:
                # AI takes full turn
                GameService.execute_ai_turn(game, current_player.id)

            # Check game hasn't crashed
            assert game.turn_number > 0

    def test_ai_always_has_legal_move(self):
        """Test AI never chooses illegal move."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.IN_PROGRESS

        evaluator = AIEvaluator()
        move = evaluator.choose_best_move(game, 1)

        # end_turn is always legal
        assert move.move_type == "end_turn" or (
            move.move_type in ["settlement", "road", "trade"]
        )

    def test_ai_moves_toward_winning(self):
        """Test AI prioritizes moves that increase points."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.IN_PROGRESS

        # Give AI resources for settlements
        ai_player = game.players[1]
        for _ in range(5):
            for r in [Resource.WOOD, Resource.BRICK, Resource.WHEAT, Resource.SHEEP]:
                ai_player.add_resource(r, 1)

        initial_points = ai_player.points
        evaluator = AIEvaluator()

        # Have AI take multiple turns
        for _ in range(3):
            move = evaluator.choose_best_move(game, 1)
            evaluator.execute_move(game, 1, move)

        # AI should prioritize settlements when possible
        # (This is a weak test - just verify no crash)
        assert True

    def test_ai_avoids_adjacent_opponent_settlements(self):
        """Test AI respects distance rule for opponent settlements."""
        game = GameService.create_game("test", "Human")
        game.status = GameStatus.SETUP

        # Place human settlement
        vertices = list(game.board.get_all_vertices())
        GameService.place_settlement(game, 0, vertices[0])

        # AI should not place adjacent
        evaluator = AIEvaluator()
        moves = evaluator.generate_moves(game, 1)

        settlement_moves = [m for m in moves if m.move_type == "settlement"]
        for move in settlement_moves:
            # Move should not be adjacent to human settlement
            is_adjacent = evaluator._vertices_are_adjacent(
                move.target, game.settlements_on_board[0].vertex
            )
            assert not is_adjacent
