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

        # Check vertex is empty
        if any(s.vertex == vertex for s in game.settlements_on_board):
            return False, "Vertex is already occupied"

        # Check adjacency rule: can't be adjacent to opponent settlements
        for settlement in game.settlements_on_board:
            if settlement.owner_id != player_id:
                if GameService._vertices_are_adjacent(game.board, vertex, settlement.vertex):
                    return False, "Settlement too close to opponent settlement"

        # In setup phase, allow placement. Otherwise check resources
        if game.status != GameStatus.SETUP:
            if not player.can_afford(GameService.SETTLEMENT_COST):
                return False, "Not enough resources to build settlement"
            player.pay_cost(GameService.SETTLEMENT_COST)

        # Place settlement
        settlement = Settlement(owner_id=player_id, vertex=vertex)
        game.settlements_on_board.append(settlement)
        player.settlements.append(settlement)
        player.points += 1

        # Award resources from adjacent hexes (if not in setup, award immediately)
        GameService._award_resources_for_settlement(game.board, player, settlement)

        return True, ""

    @staticmethod
    def build_road(game: Game, player_id: int, edge: Edge) -> Tuple[bool, str]:
        """Build a road with validation. Returns (success, error_message)."""
        player = game.players[player_id]

        # Check edge is unoccupied
        if any(r.edge == edge for r in game.roads_on_board):
            return False, "Road already exists on this edge"

        # Check resources
        if not player.can_afford(GameService.ROAD_COST):
            return False, "Not enough resources to build road"

        # Check player has adjacent settlement or road
        if not GameService._player_can_build_on_edge(game, player_id, edge):
            return False, "No settlement or road connected to this location"

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
        """Check if player has a settlement or road adjacent to an edge."""
        # Get hexes that share this edge
        hexes = game.board.get_hexes_for_edge(edge)

        for hex_obj in hexes:
            # Get vertices of this hex
            vertices = game.board.get_vertices_for_hex(hex_obj.coord)

            # Check each vertex
            for vertex in vertices:
                # Check if player has settlement here
                if any(s.vertex == vertex and s.owner_id == player_id
                       for s in game.settlements_on_board):
                    return True

                # Check if player has road adjacent to this vertex
                edges_for_vertex = GameService._get_edges_for_vertex(
                    game.board, vertex
                )
                for edge_near_vertex in edges_for_vertex:
                    if any(r.edge == edge_near_vertex and r.owner_id == player_id
                           for r in game.roads_on_board):
                        return True

        return False

    @staticmethod
    def _get_edges_for_vertex(board: Board, vertex: Vertex) -> List[Edge]:
        """Get all edges that have this vertex as an endpoint."""
        edges = []
        for edge in board.get_all_edges():
            # Check if vertex is shared by the two hexes of the edge
            if vertex in [
                Vertex((edge.hex1, edge.hex2, h.coord))
                for h in board.get_hexes_for_edge(edge)
            ]:
                # This is a simplification - proper implementation would check
                # if the vertex is actually an endpoint of the edge
                pass
        # For MVP, simplified: just return edges adjacent to the hexes in the vertex
        edges_set = set()
        for hex_coord in vertex.hex_coords:
            if board.hex_exists(hex_coord):
                edges_set.update(board.get_edges_for_hex(hex_coord))
        return list(edges_set)

    @staticmethod
    def get_valid_settlement_vertices(game: Game, player_id: int) -> List[Vertex]:
        """Get all vertices where a player can place a settlement."""
        valid = []
        for vertex in game.board.get_all_vertices():
            success, _ = GameService.place_settlement(game, player_id, vertex)
            if success:
                valid.append(vertex)
                # Undo the placement
                game.settlements_on_board = [
                    s for s in game.settlements_on_board if s.vertex != vertex
                ]
                player = game.players[player_id]
                player.settlements = [
                    s for s in player.settlements if s.vertex != vertex
                ]
                player.points -= 1
        return valid
