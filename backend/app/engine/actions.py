"""Action vocabulary for the engine — the single move representation used by
legal_actions()/apply_action(), the API layer, and (later) the trainer."""
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    # Setup + building (BUILD_* are reused, free, during the setup snake draft)
    BUILD_SETTLEMENT = "build_settlement"   # value: Vertex
    BUILD_ROAD = "build_road"               # value: Edge
    BUILD_CITY = "build_city"               # value: Vertex
    # Turn flow
    ROLL = "roll"                           # value: None (dice come from state.rng)
    END_TURN = "end_turn"                   # value: None
    # Robber pipeline
    DISCARD = "discard"                     # value: Resource (one card at a time)
    MOVE_ROBBER = "move_robber"             # value: HexCoord (steal resolves via rng)
    # Development cards
    BUY_DEV_CARD = "buy_dev_card"           # value: None (draw from shuffled deck)
    PLAY_KNIGHT = "play_knight"             # value: None (then MOVE_ROBBER phase)
    PLAY_ROAD_BUILDING = "play_road_building"  # value: None (2 free road placements)
    PLAY_YEAR_OF_PLENTY = "play_year_of_plenty"  # value: tuple of 0-2 Resources
    PLAY_MONOPOLY = "play_monopoly"         # value: Resource
    # Trading (maritime only — D1)
    MARITIME_TRADE = "maritime_trade"       # value: (give Resource, receive Resource)


@dataclass(frozen=True)
class Action:
    """One legal move by one player. Hashable and comparable so membership
    checks and dict-keyed statistics (for the future trainer) just work."""
    player: int
    type: ActionType
    value: Any = None
