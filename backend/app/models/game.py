from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from .board import Board, HexCoord, Vertex, Edge, Resource


class PlayerType(str, Enum):
    HUMAN = "human"
    AI = "ai"


@dataclass
class Settlement:
    """A settlement on the board."""
    owner_id: int
    vertex: Vertex
    points: int = 1

    def __hash__(self):
        return hash((self.owner_id, self.vertex))


@dataclass
class Road:
    """A road connecting two vertices."""
    owner_id: int
    edge: Edge

    def __hash__(self):
        return hash((self.owner_id, self.edge))


@dataclass
class Player:
    """A player in the game."""
    id: int
    name: str
    player_type: PlayerType
    color: str  # hex color code
    resources: Dict[Resource, int] = field(default_factory=lambda: {
        Resource.WOOD: 0,
        Resource.WHEAT: 0,
        Resource.ORE: 0,
        Resource.BRICK: 0,
        Resource.SHEEP: 0,
    })
    settlements: List[Settlement] = field(default_factory=list)
    roads: List[Road] = field(default_factory=list)
    points: int = 0

    def has_settlement_at(self, vertex: Vertex) -> bool:
        """Check if player has a settlement at a vertex."""
        return any(s.vertex == vertex for s in self.settlements)

    def has_road_at(self, edge: Edge) -> bool:
        """Check if player has a road at an edge."""
        return any(r.edge == edge for r in self.roads)

    def get_adjacent_vertices(self) -> List[Vertex]:
        """Get all vertices adjacent to this player's settlements/roads."""
        adjacent = set()
        for settlement in self.settlements:
            # Get neighboring vertices
            for vertex in settlement.vertex:
                # This is not quite right - we need to implement get_neighboring_vertices properly
                pass
        return list(adjacent)

    def add_resource(self, resource: Resource, count: int = 1):
        """Add resources to player's inventory."""
        self.resources[resource] = self.resources.get(resource, 0) + count

    def remove_resource(self, resource: Resource, count: int = 1) -> bool:
        """Remove resources from player's inventory. Returns True if successful."""
        if self.resources.get(resource, 0) >= count:
            self.resources[resource] -= count
            return True
        return False

    def can_afford(self, costs: Dict[Resource, int]) -> bool:
        """Check if player has enough resources for a cost."""
        for resource, cost in costs.items():
            if self.resources.get(resource, 0) < cost:
                return False
        return True

    def pay_cost(self, costs: Dict[Resource, int]) -> bool:
        """Deduct cost resources. Returns True if successful."""
        if not self.can_afford(costs):
            return False
        for resource, cost in costs.items():
            self.remove_resource(resource, cost)
        return True


class GameStatus(str, Enum):
    SETUP = "setup"
    IN_PROGRESS = "in_progress"
    WON = "won"


@dataclass
class Game:
    """Main game state."""
    id: str
    players: List[Player]
    board: Board
    current_player_id: int = 0
    turn_number: int = 0
    status: GameStatus = GameStatus.SETUP
    settlements_on_board: List[Settlement] = field(default_factory=list)
    roads_on_board: List[Road] = field(default_factory=list)
    last_dice_roll: Optional[int] = None

    @staticmethod
    def create(game_id: str, human_name: str) -> "Game":
        """Create a new game with human vs. AI."""
        players = [
            Player(id=0, name=human_name, player_type=PlayerType.HUMAN, color="#FF6B6B"),
            Player(id=1, name="AI Opponent", player_type=PlayerType.AI, color="#4ECDC4"),
        ]
        return Game(
            id=game_id,
            players=players,
            board=Board(),
            current_player_id=0,
        )

    def get_current_player(self) -> Player:
        """Get the player whose turn it is."""
        return self.players[self.current_player_id]

    def get_other_players(self) -> List[Player]:
        """Get all players except current player."""
        return [p for p in self.players if p.id != self.current_player_id]

    def next_turn(self):
        """Advance to next player's turn."""
        self.current_player_id = (self.current_player_id + 1) % len(self.players)
        self.turn_number += 1
        # Fresh turn: the new current player has not rolled yet
        self.last_dice_roll = None

    def can_place_settlement(self, player_id: int, vertex: Vertex) -> bool:
        """Check if a player can legally place a settlement at a vertex.
        Rules:
        - Vertex must be empty
        - Cannot be adjacent to opponent settlements (distance rule)
        """
        # Check if vertex is occupied
        if any(s.vertex == vertex for s in self.settlements_on_board):
            return False

        # Check if vertex is adjacent to opponent settlements
        # Neighbors are vertices that share an edge with this vertex
        for settlement in self.settlements_on_board:
            if settlement.owner_id != player_id:
                # Check if settlements are adjacent (distance rule)
                adjacent_vertices = self.board.get_neighboring_vertices(vertex)
                if any(av == settlement.vertex for av in adjacent_vertices):
                    return False

        return True

    def can_build_road(self, player_id: int, edge: Edge) -> bool:
        """Check if a player can legally build a road on an edge.
        Rules:
        - Edge must be unoccupied
        - Player must have settlement or road adjacent to this edge
        """
        # Check if edge is occupied
        if any(r.edge == edge for r in self.roads_on_board):
            return False

        # Check if player has settlement or road adjacent to this edge
        hexes = self.board.get_hexes_for_edge(edge)
        for hex_obj in hexes:
            # Get vertices of this hex that are endpoints of the edge
            # This is complex - for MVP, require player to have settlement/road
            # connected to this edge through the board graph
            pass

        return True

    def place_settlement(self, player_id: int, vertex: Vertex) -> bool:
        """Place a settlement for a player."""
        if not self.can_place_settlement(player_id, vertex):
            return False

        player = self.players[player_id]
        settlement = Settlement(owner_id=player_id, vertex=vertex)
        self.settlements_on_board.append(settlement)
        player.settlements.append(settlement)
        player.points += 1

        # Award initial resources from adjacent hexes
        self._award_resources_for_settlement(settlement)
        return True

    def build_road(self, player_id: int, edge: Edge) -> bool:
        """Build a road for a player."""
        if not self.can_build_road(player_id, edge):
            return False

        player = self.players[player_id]
        road = Road(owner_id=player_id, edge=edge)
        self.roads_on_board.append(road)
        player.roads.append(road)
        return True

    def _award_resources_for_settlement(self, settlement: Settlement):
        """Award resources to a player based on hexes adjacent to their settlement."""
        player = self.players[settlement.owner_id]
        hexes = self.board.get_hexes_for_vertex(settlement.vertex)
        for hex_obj in hexes:
            if hex_obj.resource:
                player.add_resource(hex_obj.resource, 1)

    def distribute_resources(self, dice_roll: int):
        """Distribute resources to all players based on dice roll."""
        self.last_dice_roll = dice_roll
        if dice_roll == 7:
            # TODO: Robber mechanics
            return

        hexes = self.board.get_hexes_by_dice_number(dice_roll)
        for hex_obj in hexes:
            for settlement in self.settlements_on_board:
                # Check if settlement is on a vertex of this hex
                if hex_obj in self.board.get_hexes_for_vertex(settlement.vertex):
                    player = self.players[settlement.owner_id]
                    if hex_obj.resource:
                        player.add_resource(hex_obj.resource, 1)

    def check_win_condition(self) -> Optional[int]:
        """Check if any player has reached 10 points. Return winner player_id or None."""
        for player in self.players:
            if player.points >= 10:
                self.status = GameStatus.WON
                return player.id
        return None

    def get_settlement_cost(self) -> Dict[Resource, int]:
        """Get resource cost to build a settlement."""
        return {
            Resource.WOOD: 1,
            Resource.BRICK: 1,
            Resource.WHEAT: 1,
            Resource.SHEEP: 1,
        }

    def get_road_cost(self) -> Dict[Resource, int]:
        """Get resource cost to build a road."""
        return {
            Resource.WOOD: 1,
            Resource.BRICK: 1,
        }
