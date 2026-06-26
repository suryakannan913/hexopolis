import random
from typing import Dict, List, Optional, Tuple
from app.models.game import Game, Player, Settlement, Road, Resource, GameStatus
from app.models.board import Board, HexCoord, Vertex, Edge


class GameService:
    """Service layer for game logic and validation."""

    # Game constants
    SETTLEMENT_COST = {
        Resource.WOOD: 1,
        Resource.BRICK: 1,
        Resource.WHEAT: 1,
        Resource.SHEEP: 1,
    }
    ROAD_COST = {
        Resource.WOOD: 1,
        Resource.BRICK: 1,
    }
    WINNING_POINTS = 10
    INITIAL_SETTLEMENTS_PER_PLAYER = 2

    @staticmethod
    def create_game(game_id: str, player_name: str) -> Game:
        """Create a new game with human vs. AI."""
        game = Game.create(game_id, player_name)
        # Start in setup phase for initial settlement placement
        game.status = GameStatus.SETUP
        return game

    @staticmethod
    def place_settlement(
        game: Game, player_id: int, vertex: Vertex
    ) -> Tuple[bool, str]:
        """Place a settlement with validation. Returns (success, error_message)."""
        player = game.players[player_id]
        is_setup = game.status == GameStatus.SETUP

        # Vertex must be a real board location
        if vertex not in game.board.get_all_vertices():
            return False, "Invalid settlement location"

        # Check vertex is empty
        if any(s.vertex == vertex for s in game.settlements_on_board):
            return False, "Vertex is already occupied"

        # Distance rule: can't be adjacent to ANY existing settlement
        for settlement in game.settlements_on_board:
            if GameService._vertices_are_adjacent(game.board, vertex, settlement.vertex):
                return False, "Settlement too close to another settlement"

        if not is_setup:
            # Must connect to one of the player's own roads
            if not GameService._player_connects_to_vertex(game, player_id, vertex):
                return False, "Settlement must connect to one of your roads"
            if not player.can_afford(GameService.SETTLEMENT_COST):
                return False, "Not enough resources to build settlement"
            player.pay_cost(GameService.SETTLEMENT_COST)

        # Place settlement
        settlement = Settlement(owner_id=player_id, vertex=vertex)
        game.settlements_on_board.append(settlement)
        player.settlements.append(settlement)
        player.points += 1

        # Setup settlements grant a starting hand from adjacent hexes
        if is_setup:
            GameService._award_resources_for_settlement(game.board, player, settlement)
            GameService._advance_setup(game)

        return True, ""

    @staticmethod
    def _advance_setup(game: Game) -> None:
        """Drive the opening-placement phase.

        The human places their settlements by clicking; once they have placed
        their quota, the AI auto-places its settlements and the game begins.
        """
        per_player = GameService.INITIAL_SETTLEMENTS_PER_PLAYER
        human = game.players[0]
        ai = game.players[1]

        if len(human.settlements) < per_player:
            return  # Wait for the human to finish placing

        # Human is done — let the AI claim its opening settlements
        while len(ai.settlements) < per_player:
            vertex = GameService._best_setup_vertex(game, ai.id)
            if vertex is None:
                break
            GameService.place_settlement_setup_ai(game, ai.id, vertex)

        # Opening placement complete: begin normal play with the human
        game.status = GameStatus.IN_PROGRESS
        game.current_player_id = 0
        game.turn_number = 1

    @staticmethod
    def place_settlement_setup_ai(game: Game, player_id: int, vertex: Vertex) -> None:
        """Directly place a free AI setup settlement (no setup re-entry)."""
        player = game.players[player_id]
        settlement = Settlement(owner_id=player_id, vertex=vertex)
        game.settlements_on_board.append(settlement)
        player.settlements.append(settlement)
        player.points += 1
        GameService._award_resources_for_settlement(game.board, player, settlement)

    @staticmethod
    def _best_setup_vertex(game: Game, player_id: int):
        """Pick the highest-value legal opening vertex for the AI."""
        best, best_score = None, -1.0
        for vertex in game.board.get_all_vertices():
            if any(s.vertex == vertex for s in game.settlements_on_board):
                continue
            if any(
                GameService._vertices_are_adjacent(game.board, vertex, s.vertex)
                for s in game.settlements_on_board
            ):
                continue
            score = 0.0
            for hex_obj in game.board.get_hexes_for_vertex(vertex):
                if hex_obj.resource:
                    score += 1.0
                    if hex_obj.dice_number in (6, 8):
                        score += 2.0
                    elif hex_obj.dice_number in (5, 9):
                        score += 1.0
            if score > best_score:
                best, best_score = vertex, score
        return best

    @staticmethod
    def build_road(game: Game, player_id: int, edge: Edge) -> Tuple[bool, str]:
        """Build a road with validation. Returns (success, error_message)."""
        player = game.players[player_id]

        # Edge must be a real board location
        if edge not in game.board.get_all_edges():
            return False, "Invalid road location"

        # Check edge is unoccupied
        if any(r.edge == edge for r in game.roads_on_board):
            return False, "Road already exists on this edge"

        # Check resources
        if not player.can_afford(GameService.ROAD_COST):
            return False, "Not enough resources to build road"

        # Check player has adjacent settlement or road
        if not GameService._player_can_build_on_edge(game, player_id, edge):
            return False, "Road must connect to your settlement or road"

        player.pay_cost(GameService.ROAD_COST)
        road = Road(owner_id=player_id, edge=edge)
        game.roads_on_board.append(road)
        player.roads.append(road)

        return True, ""

    @staticmethod
    def roll_dice(game: Game) -> int:
        """Roll two dice and return the sum (2-12)."""
        roll = random.randint(1, 6) + random.randint(1, 6)
        game.last_dice_roll = roll
        return roll

    @staticmethod
    def distribute_resources(game: Game, dice_roll: int) -> None:
        """Distribute resources to all players based on dice roll."""
        if dice_roll == 7:
            # TODO: Robber mechanics for MVP skip
            return

        hexes = game.board.get_hexes_by_dice_number(dice_roll)
        for hex_obj in hexes:
            for settlement in game.settlements_on_board:
                hexes_for_vertex = game.board.get_hexes_for_vertex(settlement.vertex)
                if hex_obj in hexes_for_vertex:
                    player = game.players[settlement.owner_id]
                    if hex_obj.resource:
                        player.add_resource(hex_obj.resource, 1)

    @staticmethod
    def execute_trade(
        game: Game, player_id: int, give_resources: Dict[Resource, int],
        receive_resources: Dict[Resource, int]
    ) -> Tuple[bool, str]:
        """Execute a trade with validation. Returns (success, error_message)."""
        player = game.players[player_id]

        # Check player has resources to give
        for resource, count in give_resources.items():
            if player.resources.get(resource, 0) < count:
                return False, f"Not enough {resource.value}"

        # Execute trade
        for resource, count in give_resources.items():
            player.remove_resource(resource, count)
        for resource, count in receive_resources.items():
            player.add_resource(resource, count)

        return True, ""

    @staticmethod
    def end_turn(game: Game) -> None:
        """End current player's turn and advance to next player."""
        game.next_turn()

    @staticmethod
    def check_win_condition(game: Game) -> Optional[int]:
        """Check if any player won. Returns winner player_id or None."""
        for player in game.players:
            if player.points >= GameService.WINNING_POINTS:
                game.status = GameStatus.WON
                return player.id
        return None

    # Private helper methods

    @staticmethod
    def _vertices_are_adjacent(board: Board, v1: Vertex, v2: Vertex) -> bool:
        """Check if two vertices are adjacent (share an edge)."""
        # Two vertices are adjacent if they share exactly 2 hexes
        shared = set(v1.hex_coords) & set(v2.hex_coords)
        return len(shared) == 2

    @staticmethod
    def _award_resources_for_settlement(
        board: Board, player: Player, settlement: Settlement
    ) -> None:
        """Award resources from hexes adjacent to a settlement."""
        hexes = board.get_hexes_for_vertex(settlement.vertex)
        for hex_obj in hexes:
            if hex_obj.resource:
                player.add_resource(hex_obj.resource, 1)

    @staticmethod
    def _player_can_build_on_edge(game: Game, player_id: int, edge: Edge) -> bool:
        """A road is buildable if it touches one of the player's settlements or roads."""
        endpoints = game.board.get_edge_endpoints(edge)
        endpoint_set = set(endpoints)

        # Connected to one of the player's own settlements
        for s in game.settlements_on_board:
            if s.owner_id == player_id and s.vertex in endpoint_set:
                return True

        # Connected to one of the player's own roads (shares an endpoint vertex)
        for r in game.roads_on_board:
            if r.owner_id != player_id:
                continue
            if endpoint_set & set(game.board.get_edge_endpoints(r.edge)):
                return True

        return False

    @staticmethod
    def _player_connects_to_vertex(game: Game, player_id: int, vertex: Vertex) -> bool:
        """A settlement (in normal play) must sit on one of the player's roads."""
        incident_edges = set(game.board.get_edges_for_vertex(vertex))
        return any(
            r.owner_id == player_id and r.edge in incident_edges
            for r in game.roads_on_board
        )

    @staticmethod
    def execute_ai_turn(game: Game, player_id: int) -> None:
        """Execute a full AI turn."""
        from app.ai.evaluator import AIPlayer

        ai = AIPlayer(player_id)
        ai.take_turn(game)
