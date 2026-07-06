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

    # NOTE: All rules (placement, building, dice distribution, win check, costs)
    # live in the single source of truth, GameService (app/services/game_service.py).
    # Game is a pure state container: it holds data and trivial state transitions
    # only. Do not reintroduce rule logic here.
