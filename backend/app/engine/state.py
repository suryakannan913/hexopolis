"""Engine game state — pure data plus trivial derived values.

All rules (legality, mutation) live in rules.py; nothing here validates moves.
The state owns a seeded random.Random (Step 3): dice rolls, board generation,
dev-card draws, and robber steals all draw from it, so a seed fully determines
a game given the same action sequence.
"""
import copy as _copy
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.models.board import Board, Edge, HexCoord, Resource, Vertex


class Phase(str, Enum):
    SETUP_SETTLEMENT = "setup_settlement"
    SETUP_ROAD = "setup_road"
    MAIN = "main"
    DISCARD = "discard"
    MOVE_ROBBER = "move_robber"
    GAME_OVER = "game_over"


class DevCard(str, Enum):
    KNIGHT = "knight"
    VICTORY_POINT = "victory_point"
    ROAD_BUILDING = "road_building"
    YEAR_OF_PLENTY = "year_of_plenty"
    MONOPOLY = "monopoly"


# Building kinds (values in GameState.buildings)
SETTLEMENT = "settlement"
CITY = "city"

# Ruleset constants (CATAN_1V1_RULES.md)
WINNING_POINTS = 15               # §12 / D8 (1v1 target)
DISCARD_LIMIT = 9                 # §6 / D2: discard half when holding MORE THAN 9
FRIENDLY_ROBBER_VISIBLE_VP = 2    # §6.1 / D9
LONGEST_ROAD_MIN = 5              # §11
LARGEST_ARMY_MIN = 3              # §11
BANK_PER_RESOURCE = 19            # §1 / D3 (finite bank)
SETUP_ORDER = (0, 1, 1, 0)        # §3 snake draft

ROAD_COST = {Resource.WOOD: 1, Resource.BRICK: 1}
SETTLEMENT_COST = {Resource.WOOD: 1, Resource.BRICK: 1, Resource.SHEEP: 1, Resource.WHEAT: 1}
CITY_COST = {Resource.ORE: 3, Resource.WHEAT: 2}
DEV_CARD_COST = {Resource.ORE: 1, Resource.SHEEP: 1, Resource.WHEAT: 1}

# §1: 14 Knight, 5 VP, 2 Road Building, 2 Year of Plenty, 2 Monopoly
DEV_DECK_COMPOSITION = (
    [DevCard.KNIGHT] * 14
    + [DevCard.VICTORY_POINT] * 5
    + [DevCard.ROAD_BUILDING] * 2
    + [DevCard.YEAR_OF_PLENTY] * 2
    + [DevCard.MONOPOLY] * 2
)


def zero_resources() -> Dict[Resource, int]:
    return {r: 0 for r in Resource}


def zero_devs() -> Dict[DevCard, int]:
    return {c: 0 for c in DevCard}


@dataclass
class PlayerState:
    id: int
    name: str
    resources: Dict[Resource, int] = field(default_factory=zero_resources)
    dev_hand: Dict[DevCard, int] = field(default_factory=zero_devs)
    dev_bought_this_turn: Dict[DevCard, int] = field(default_factory=zero_devs)
    knights_played: int = 0
    # Piece supplies (§8)
    roads_left: int = 15
    settlements_left: int = 5
    cities_left: int = 4

    def hand_size(self) -> int:
        return sum(self.resources.values())


@dataclass
class GameState:
    board: Board
    ports: Dict[Vertex, Optional[Resource]]  # vertex -> port (None = generic 3:1)
    robber: HexCoord
    players: List[PlayerState]
    rng: random.Random
    seed: int
    bank: Dict[Resource, int] = field(default_factory=lambda: {r: BANK_PER_RESOURCE for r in Resource})
    dev_deck: List[DevCard] = field(default_factory=list)
    buildings: Dict[Vertex, Tuple[int, str]] = field(default_factory=dict)  # vertex -> (owner, kind)
    roads: Dict[Edge, int] = field(default_factory=dict)                    # edge -> owner
    phase: Phase = Phase.SETUP_SETTLEMENT
    current_player: int = 0
    turn_number: int = 0
    setup_index: int = 0
    setup_anchor: Optional[Vertex] = None      # settlement the setup road must touch
    has_rolled: bool = False
    dev_played_this_turn: bool = False
    free_roads_pending: int = 0                # from Road Building
    discard_quota: List[int] = field(default_factory=lambda: [0, 0])
    last_roll: Optional[Tuple[int, int]] = None
    longest_road_owner: Optional[int] = None
    largest_army_owner: Optional[int] = None
    winner: Optional[int] = None

    # ---- the interface bots and the future trainer rely on ----

    def copy(self) -> "GameState":
        """Deep copy, including the RNG's internal state: a copy plays out the
        same future as the original for the same action sequence."""
        return _copy.deepcopy(self)

    def is_terminal(self) -> bool:
        return self.winner is not None

    def actor(self) -> int:
        """Player who must decide next (differs from current_player only while
        the opponent is discarding on a 7)."""
        if self.phase == Phase.DISCARD:
            for pid in (self.current_player, 1 - self.current_player):
                if self.discard_quota[pid] > 0:
                    return pid
        return self.current_player

    # ---- derived values ----

    def settlements_of(self, pid: int) -> List[Vertex]:
        return [v for v, (o, k) in self.buildings.items() if o == pid and k == SETTLEMENT]

    def cities_of(self, pid: int) -> List[Vertex]:
        return [v for v, (o, k) in self.buildings.items() if o == pid and k == CITY]

    def roads_of(self, pid: int) -> List[Edge]:
        return [e for e, o in self.roads.items() if o == pid]

    def visible_vp(self, pid: int) -> int:
        """Public VP: settlements + cities + Longest Road + Largest Army.
        Excludes hidden VP dev cards (used by the friendly-robber rule, §6.1)."""
        vp = len(self.settlements_of(pid)) + 2 * len(self.cities_of(pid))
        if self.longest_road_owner == pid:
            vp += 2
        if self.largest_army_owner == pid:
            vp += 2
        return vp

    def total_vp(self, pid: int) -> int:
        """True VP including hidden Victory Point cards (win check, §12)."""
        return self.visible_vp(pid) + self.players[pid].dev_hand[DevCard.VICTORY_POINT]
