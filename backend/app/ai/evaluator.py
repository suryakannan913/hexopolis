from dataclasses import dataclass
from typing import List, Tuple, Optional
from app.models.game import Game, Player, Resource
from app.models.board import Vertex, Edge, HexCoord


@dataclass
class Move:
    """Represents a possible move."""
    move_type: str  # 'settlement', 'road', 'trade', 'end_turn'
    target: Optional[object] = None  # Vertex, Edge, or trade data
    score: float = 0.0

    def __repr__(self):
        return f"Move({self.move_type}, score={self.score:.1f})"


class AIEvaluator:
    """AI opponent that evaluates game states and makes strategic decisions."""

    # Heuristic weights for scoring
    SETTLEMENT_VALUE = 100.0  # Settlement scores 1 point; weight heavily
    ROAD_VALUE = 5.0  # Road helps connect settlements
    RESOURCE_VALUE = 0.5  # Each resource slightly valuable
    OPPONENT_SETTLEMENT_PENALTY = 50.0  # Blocking opponent is valuable
    DISTANCE_TO_WIN = 10.0  # Encourage pushing toward 10 points

    # Trade heuristics
    BANK_TRADE_RATIO = 4  # 4:1 bank trades
    FAVORABLE_TRADE_RATIO = 2  # 2:1 for favorable resource swaps

    def __init__(self, lookahead_depth: int = 1):
        """Initialize AI with optional lookahead depth (1 = greedy, 2+ = minimax)."""
        self.lookahead_depth = lookahead_depth

    def evaluate_state(self, game: Game, player_id: int) -> float:
        """Score a game state from the given player's perspective."""
        player = game.players[player_id]
        opponent = game.players[1 - player_id]

        score = 0.0

        # Score own settlements and positions
        score += player.points * self.SETTLEMENT_VALUE

        # Score roads (help toward next settlement)
        score += len(player.roads) * self.ROAD_VALUE

        # Score resources (value of having diverse resources)
        for resource, count in player.resources.items():
            score += count * self.RESOURCE_VALUE

        # Bonus for being close to winning
        if player.points >= 8:
            score += (player.points - 8) * self.DISTANCE_TO_WIN

        # Penalty for opponent progress
        score -= opponent.points * self.SETTLEMENT_VALUE * 0.7

        # Bonus for blocking opponent settlements
        score -= len(opponent.roads) * self.ROAD_VALUE * 0.3

        return score

    def generate_moves(self, game: Game, player_id: int) -> List[Move]:
        """Generate all legal moves for a player in current state."""
        from app.services.game_service import GameService

        moves = []
        player = game.players[player_id]

        # 1. Settlement moves (if can afford)
        if player.can_afford(GameService.SETTLEMENT_COST) or game.status.value == "setup":
            for vertex in game.board.get_all_vertices():
                # Check if settlement can be placed
                if self._can_place_settlement(game, player_id, vertex):
                    move = Move(
                        move_type="settlement",
                        target=vertex,
                        score=self._score_settlement(game, player_id, vertex),
                    )
                    moves.append(move)

        # 2. Road moves — only build roads to enable future settlements, and
        #    cap them so the AI doesn't hoard roads instead of settling.
        has_settlement_move = any(m.move_type == "settlement" for m in moves)
        road_budget = len(player.settlements) * 2 + 1
        if (
            player.can_afford(GameService.ROAD_COST)
            and not has_settlement_move
            and len(player.roads) < road_budget
        ):
            for edge in game.board.get_all_edges():
                if self._can_build_road(game, player_id, edge):
                    move = Move(
                        move_type="road",
                        target=edge,
                        score=self._score_road(game, player_id, edge),
                    )
                    moves.append(move)

        # 3. Trade moves (if has resources to trade)
        trade_moves = self._generate_trade_moves(game, player_id)
        moves.extend(trade_moves)

        # 4. Always have end_turn as fallback
        moves.append(Move(move_type="end_turn", score=0.0))

        # Sort by score descending
        moves.sort(key=lambda m: m.score, reverse=True)

        return moves

    def choose_best_move(self, game: Game, player_id: int) -> Move:
        """Choose best move using greedy or minimax strategy."""
        moves = self.generate_moves(game, player_id)

        if not moves:
            return Move(move_type="end_turn")

        # Greedy: just pick highest-scoring move
        best_move = moves[0]

        # Optional: minimax lookahead (simplified version)
        if self.lookahead_depth > 1 and best_move.move_type != "end_turn":
            # Simulate move and check result quality
            # For MVP, skip this complexity
            pass

        return best_move

    def execute_move(self, game: Game, player_id: int, move: Move) -> bool:
        """Execute a chosen move. Returns True if successful."""
        from app.services.game_service import GameService

        if move.move_type == "settlement":
            success, _ = GameService.place_settlement(game, player_id, move.target)
            return success

        elif move.move_type == "road":
            success, _ = GameService.build_road(game, player_id, move.target)
            return success

        elif move.move_type == "trade":
            give, receive = move.target
            success, _ = GameService.execute_trade(game, player_id, give, receive)
            return success

        elif move.move_type == "end_turn":
            GameService.end_turn(game)
            return True

        return False

    # Private helper methods

    def _can_place_settlement(self, game: Game, player_id: int, vertex: Vertex) -> bool:
        """Check if settlement can be placed (without modifying game state)."""
        from app.services.game_service import GameService

        # Check vertex is empty
        if any(s.vertex == vertex for s in game.settlements_on_board):
            return False

        # Distance rule: not adjacent to ANY settlement
        for settlement in game.settlements_on_board:
            if self._vertices_are_adjacent(vertex, settlement.vertex):
                return False

        # Outside setup, must connect to one of the player's own roads
        if game.status.value != "setup":
            return GameService._player_connects_to_vertex(game, player_id, vertex)

        return True

    def _can_build_road(self, game: Game, player_id: int, edge: Edge) -> bool:
        """Check if road can be built (without modifying game state)."""
        from app.services.game_service import GameService

        # Check edge is unoccupied
        if any(r.edge == edge for r in game.roads_on_board):
            return False

        return GameService._player_can_build_on_edge(game, player_id, edge)

    def _score_settlement(self, game: Game, player_id: int, vertex: Vertex) -> float:
        """Score the value of placing a settlement at a vertex."""
        score = 0.0

        # Base value: settlements are worth points
        score += self.SETTLEMENT_VALUE

        # Bonus: resources produced
        hexes = game.board.get_hexes_for_vertex(vertex)
        for hex_obj in hexes:
            if hex_obj.resource:
                # Prefer high-probability rolls
                if hex_obj.dice_number in [6, 8]:
                    score += 2.0
                elif 5 <= hex_obj.dice_number <= 9:
                    score += 1.0

        # Penalty: blocks opponent
        for settlement in game.settlements_on_board:
            if settlement.owner_id != player_id:
                if self._vertices_are_adjacent(vertex, settlement.vertex):
                    score -= self.OPPONENT_SETTLEMENT_PENALTY * 0.5

        return score

    def _score_road(self, game: Game, player_id: int, edge: Edge) -> float:
        """Score the value of building a road on an edge."""
        score = self.ROAD_VALUE

        # Bonus if road leads toward a possible settlement location
        player = game.players[player_id]
        if len(player.settlements) > 0:
            score += 2.0  # Road network valuable if already have settlements

        return score

    def _generate_trade_moves(self, game: Game, player_id: int) -> List[Move]:
        """Generate possible trade moves."""
        from app.services.game_service import GameService

        moves = []
        player = game.players[player_id]

        # Simple strategy: 4:1 trades to get toward next settlement
        settlement_cost = GameService.SETTLEMENT_COST

        # Find missing resources for settlement
        for needed_resource in settlement_cost:
            if player.resources.get(needed_resource, 0) == 0:
                # AI has excess of some resource, trade for this one
                for have_resource in player.resources:
                    if (
                        player.resources.get(have_resource, 0) >= 4
                        and have_resource != needed_resource
                    ):
                        give = {have_resource: 4}
                        receive = {needed_resource: 1}
                        move = Move(
                            move_type="trade",
                            target=(give, receive),
                            score=5.0,  # Modest score for trades
                        )
                        moves.append(move)

        return moves

    def _vertices_are_adjacent(self, v1: Vertex, v2: Vertex) -> bool:
        """Check if two vertices are adjacent."""
        # Two vertices are adjacent if they share exactly 2 hexes
        shared = set(v1.hex_coords) & set(v2.hex_coords)
        return len(shared) == 2


# Import GameService for move execution
# (avoid circular imports by importing inside methods where needed)


class AIPlayer:
    """Wrapper for AI player that manages AI turns."""

    def __init__(self, player_id: int, evaluator: Optional[AIEvaluator] = None):
        self.player_id = player_id
        self.evaluator = evaluator or AIEvaluator()

    def take_turn(self, game: Game) -> None:
        """Execute a full AI turn: roll, then build until nothing useful remains."""
        from app.services.game_service import GameService

        # Roll dice and collect resources
        dice_roll = GameService.roll_dice(game)
        GameService.distribute_resources(game, dice_roll)

        # Keep taking build/trade actions until only end_turn is best (or cap out)
        for _ in range(10):
            move = self.evaluator.choose_best_move(game, self.player_id)
            if move.move_type == "end_turn":
                break
            if not self.evaluator.execute_move(game, self.player_id, move):
                break  # Move failed validation; stop to avoid looping
            if GameService.check_win_condition(game):
                return  # Game over — leave turn with the winner

        GameService.end_turn(game)
