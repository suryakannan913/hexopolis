from pydantic import BaseModel
from typing import Dict, List, Optional
from app.models.board import Resource
from app.models.game import GameStatus, PlayerType


class HexCoordSchema(BaseModel):
    """Hex coordinate."""
    q: int
    r: int


class VertexSchema(BaseModel):
    """Vertex (settlement location)."""
    hex_coords: List[tuple[int, int]]


class EdgeSchema(BaseModel):
    """Edge (road location)."""
    hex1: tuple[int, int]
    hex2: tuple[int, int]


class HexSchema(BaseModel):
    """A single hex on the board."""
    coord: HexCoordSchema
    resource: Optional[str]
    dice_number: Optional[int]


class SettlementSchema(BaseModel):
    """A settlement on the board."""
    owner_id: int
    points: int = 1


class RoadSchema(BaseModel):
    """A road on the board."""
    owner_id: int


class PlayerSchema(BaseModel):
    """A player in the game."""
    id: int
    name: str
    player_type: str
    color: str
    resources: Dict[str, int]
    points: int
    settlements_count: int
    roads_count: int


class BoardHexSchema(BaseModel):
    """A board hex with its position, resource, and dice number."""
    q: int
    r: int
    resource: Optional[str]
    dice_number: Optional[int]


class BoardSettlementSchema(BaseModel):
    """A placed settlement, with the 3 hex coords defining its vertex."""
    owner_id: int
    color: str
    vertex_coords: List[tuple[int, int]]


class BoardRoadSchema(BaseModel):
    """A placed road, defined by the two hex coords it borders."""
    owner_id: int
    color: str
    hex1: tuple[int, int]
    hex2: tuple[int, int]


class GameStateSchema(BaseModel):
    """Complete game state."""
    id: str
    status: str
    current_player_id: int
    current_player_name: str
    turn_number: int
    last_dice_roll: Optional[int]
    players: List[PlayerSchema]
    settlements_count: int
    roads_count: int
    board: List[BoardHexSchema]
    settlements: List[BoardSettlementSchema]
    roads: List[BoardRoadSchema]
    setup_complete: bool


class GameCreateRequest(BaseModel):
    """Request to create a new game."""
    player_name: str


class GameCreateResponse(BaseModel):
    """Response when creating a new game."""
    game_id: str
    status: str
    message: str


class RollDiceResponse(BaseModel):
    """Response from rolling dice."""
    dice_roll: int
    success: bool


class BuildSettlementRequest(BaseModel):
    """Request to build a settlement."""
    vertex_coords: List[tuple[int, int]]


class BuildRoadRequest(BaseModel):
    """Request to build a road."""
    hex1_coords: tuple[int, int]
    hex2_coords: tuple[int, int]


class BuildResponse(BaseModel):
    """Response from building."""
    success: bool
    message: str


class TradeRequest(BaseModel):
    """Request to execute a trade."""
    give_resources: Dict[str, int]
    receive_resources: Dict[str, int]


class TradeResponse(BaseModel):
    """Response from trading."""
    success: bool
    message: str


class EndTurnResponse(BaseModel):
    """Response from ending turn."""
    success: bool
    next_player_id: int
    next_player_name: str


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool
    message: str
    error_code: str
