from fastapi import APIRouter, HTTPException, status
from typing import Dict
from app.models.game import Game
from app.models.board import HexCoord, Vertex, Edge, Resource
from app.services.game_service import GameService
from app.models.game import GameStatus
from app.schemas.game_schema import (
    GameCreateRequest,
    GameCreateResponse,
    RollDiceResponse,
    BuildSettlementRequest,
    BuildRoadRequest,
    BuildResponse,
    TradeRequest,
    TradeResponse,
    EndTurnResponse,
    GameStateSchema,
    PlayerSchema,
    BoardHexSchema,
    BoardSettlementSchema,
    BoardRoadSchema,
)

router = APIRouter(prefix="/game", tags=["game"])

# In-memory game storage (for MVP; will migrate to database in Phase 2)
games_db: Dict[str, Game] = {}
game_counter = 0


def _get_game_or_404(game_id: str) -> Game:
    """Get game by ID or raise 404."""
    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game not found")
    return games_db[game_id]


def _game_state_to_schema(game: Game) -> GameStateSchema:
    """Convert game object to response schema."""
    players_schema = []
    for player in game.players:
        players_schema.append(
            PlayerSchema(
                id=player.id,
                name=player.name,
                player_type=player.player_type.value,
                color=player.color,
                resources={r.value: player.resources[r] for r in Resource},
                points=player.points,
                settlements_count=len(player.settlements),
                roads_count=len(player.roads),
            )
        )

    # Serialize the board so the frontend renders the real layout
    board_schema = [
        BoardHexSchema(
            q=hex_obj.coord.q,
            r=hex_obj.coord.r,
            resource=hex_obj.resource.value if hex_obj.resource else None,
            dice_number=hex_obj.dice_number,
        )
        for hex_obj in game.board.hexes.values()
    ]

    settlements_schema = [
        BoardSettlementSchema(
            owner_id=s.owner_id,
            color=game.players[s.owner_id].color,
            vertex_coords=[(h.q, h.r) for h in s.vertex.hex_coords],
        )
        for s in game.settlements_on_board
    ]

    roads_schema = [
        BoardRoadSchema(
            owner_id=r.owner_id,
            color=game.players[r.owner_id].color,
            hex1=(r.edge.hex1.q, r.edge.hex1.r),
            hex2=(r.edge.hex2.q, r.edge.hex2.r),
        )
        for r in game.roads_on_board
    ]

    return GameStateSchema(
        id=game.id,
        status=game.status.value,
        current_player_id=game.current_player_id,
        current_player_name=game.get_current_player().name,
        turn_number=game.turn_number,
        last_dice_roll=game.last_dice_roll,
        players=players_schema,
        settlements_count=len(game.settlements_on_board),
        roads_count=len(game.roads_on_board),
        board=board_schema,
        settlements=settlements_schema,
        roads=roads_schema,
        setup_complete=game.status != GameStatus.SETUP,
    )


@router.post("/new", response_model=GameCreateResponse, status_code=201)
def create_new_game(request: GameCreateRequest) -> GameCreateResponse:
    """Create a new game vs. AI opponent."""
    global game_counter
    game_counter += 1
    game_id = f"game-{game_counter}"

    game = GameService.create_game(game_id, request.player_name)
    games_db[game_id] = game

    return GameCreateResponse(
        game_id=game_id, status=game.status.value, message="Game created successfully"
    )


@router.get("/{game_id}", response_model=GameStateSchema)
def get_game_state(game_id: str) -> GameStateSchema:
    """Get current game state."""
    game = _get_game_or_404(game_id)
    return _game_state_to_schema(game)


@router.post("/{game_id}/roll-dice", response_model=RollDiceResponse)
def roll_dice(game_id: str) -> RollDiceResponse:
    """Roll dice and distribute resources."""
    game = _get_game_or_404(game_id)

    if game.status == GameStatus.SETUP:
        raise HTTPException(status_code=400, detail="Place your starting settlements first")
    if game.status == GameStatus.WON:
        raise HTTPException(status_code=400, detail="Game is over")
    if game.last_dice_roll is not None:
        raise HTTPException(status_code=400, detail="You already rolled this turn")

    # Roll dice
    roll = GameService.roll_dice(game)

    # Distribute resources
    GameService.distribute_resources(game, roll)

    return RollDiceResponse(dice_roll=roll, success=True)


@router.post("/{game_id}/build-settlement", response_model=BuildResponse)
def build_settlement(
    game_id: str, request: BuildSettlementRequest
) -> BuildResponse:
    """Place a settlement on the board."""
    game = _get_game_or_404(game_id)
    player = game.get_current_player()
    if game.status == GameStatus.WON:
        raise HTTPException(status_code=400, detail="Game is over")
    if player.player_type.value == "ai":
        raise HTTPException(status_code=400, detail="It's not your turn")

    # Convert coords to Vertex
    hex_coords = tuple(HexCoord(q, r) for q, r in request.vertex_coords)
    vertex = Vertex(hex_coords)

    # Place settlement
    success, error = GameService.place_settlement(game, player.id, vertex)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    # Check win condition
    GameService.check_win_condition(game)

    return BuildResponse(success=True, message="Settlement placed successfully")


@router.post("/{game_id}/build-road", response_model=BuildResponse)
def build_road(game_id: str, request: BuildRoadRequest) -> BuildResponse:
    """Build a road on the board."""
    game = _get_game_or_404(game_id)
    player = game.get_current_player()
    if game.status == GameStatus.WON:
        raise HTTPException(status_code=400, detail="Game is over")
    if player.player_type.value == "ai":
        raise HTTPException(status_code=400, detail="It's not your turn")
    if game.status == GameStatus.SETUP:
        raise HTTPException(status_code=400, detail="Roads can't be built during setup")

    # Convert coords to Edge
    hex1 = HexCoord(*request.hex1_coords)
    hex2 = HexCoord(*request.hex2_coords)
    edge = Edge(hex1, hex2)

    # Build road
    success, error = GameService.build_road(game, player.id, edge)

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return BuildResponse(success=True, message="Road built successfully")


@router.post("/{game_id}/trade", response_model=TradeResponse)
def execute_trade(game_id: str, request: TradeRequest) -> TradeResponse:
    """Execute a resource trade."""
    game = _get_game_or_404(game_id)
    player = game.get_current_player()

    # Convert resource names to enum
    give_resources = {
        Resource(r): count for r, count in request.give_resources.items()
    }
    receive_resources = {
        Resource(r): count for r, count in request.receive_resources.items()
    }

    # Execute trade
    success, error = GameService.execute_trade(
        game, player.id, give_resources, receive_resources
    )

    if not success:
        raise HTTPException(status_code=400, detail=error)

    return TradeResponse(success=True, message="Trade completed successfully")


@router.post("/{game_id}/end-turn", response_model=EndTurnResponse)
def end_turn(game_id: str) -> EndTurnResponse:
    """End current player's turn."""
    game = _get_game_or_404(game_id)

    if game.status == GameStatus.SETUP:
        raise HTTPException(status_code=400, detail="Finish placing your starting settlements first")

    GameService.end_turn(game)
    next_player = game.get_current_player()

    return EndTurnResponse(
        success=True,
        next_player_id=next_player.id,
        next_player_name=next_player.name,
    )


@router.get("/{game_id}/status")
def get_game_status(game_id: str):
    """Get brief game status."""
    game = _get_game_or_404(game_id)
    return {
        "game_id": game.id,
        "status": game.status.value,
        "current_player": game.get_current_player().name,
        "turn_number": game.turn_number,
    }


@router.post("/{game_id}/ai-turn")
def execute_ai_turn(game_id: str):
    """Execute the AI opponent's turn."""
    game = _get_game_or_404(game_id)

    # Only execute AI turn if it's actually the AI's turn
    current_player = game.get_current_player()
    if current_player.player_type.value != "ai":
        raise HTTPException(
            status_code=400,
            detail="Not the AI's turn"
        )

    GameService.execute_ai_turn(game, current_player.id)

    return {
        "success": True,
        "message": "AI turn executed",
        "next_player_id": game.get_current_player().id,
        "next_player_name": game.get_current_player().name,
    }
