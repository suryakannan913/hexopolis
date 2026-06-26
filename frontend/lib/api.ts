const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface GameStateResponse {
  id: string;
  status: string;
  current_player_id: number;
  current_player_name: string;
  turn_number: number;
  last_dice_roll: number | null;
  players: Array<{
    id: number;
    name: string;
    player_type: string;
    color: string;
    points: number;
    resources: Record<string, number>;
    settlements_count: number;
    roads_count: number;
  }>;
  settlements_count: number;
  roads_count: number;
  board: Array<{
    q: number;
    r: number;
    resource: string | null;
    dice_number: number | null;
  }>;
  settlements: Array<{
    owner_id: number;
    color: string;
    vertex_coords: [number, number][];
  }>;
  roads: Array<{
    owner_id: number;
    color: string;
    hex1: [number, number];
    hex2: [number, number];
  }>;
  setup_complete: boolean;
}

export async function createGame(playerName: string): Promise<{ game_id: string; status: string }> {
  const response = await fetch(`${API_URL}/game/new`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ player_name: playerName }),
  });

  if (!response.ok) throw new Error('Failed to create game');
  return response.json();
}

export async function getGameState(gameId: string): Promise<GameStateResponse> {
  const response = await fetch(`${API_URL}/game/${gameId}`);
  if (!response.ok) throw new Error('Failed to fetch game state');
  return response.json();
}

export async function rollDice(gameId: string): Promise<{ dice_roll: number; success: boolean }> {
  const response = await fetch(`${API_URL}/game/${gameId}/roll-dice`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to roll dice');
  return response.json();
}

export async function buildSettlement(
  gameId: string,
  vertexCoords: [number, number][]
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_URL}/game/${gameId}/build-settlement`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vertex_coords: vertexCoords }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to build settlement');
  }
  return response.json();
}

export async function buildRoad(
  gameId: string,
  hex1Coords: [number, number],
  hex2Coords: [number, number]
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_URL}/game/${gameId}/build-road`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ hex1_coords: hex1Coords, hex2_coords: hex2Coords }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to build road');
  }
  return response.json();
}

export async function executeTrade(
  gameId: string,
  giveResources: Record<string, number>,
  receiveResources: Record<string, number>
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_URL}/game/${gameId}/trade`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      give_resources: giveResources,
      receive_resources: receiveResources,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to execute trade');
  }
  return response.json();
}

export async function endTurn(gameId: string): Promise<{
  success: boolean;
  next_player_id: number;
  next_player_name: string;
}> {
  const response = await fetch(`${API_URL}/game/${gameId}/end-turn`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to end turn');
  return response.json();
}

export async function executeAITurn(gameId: string): Promise<{
  success: boolean;
  message: string;
  next_player_id: number;
  next_player_name: string;
}> {
  const response = await fetch(`${API_URL}/game/${gameId}/ai-turn`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to execute AI turn');
  }
  return response.json();
}

export async function getGameStatus(gameId: string): Promise<{
  game_id: string;
  status: string;
  current_player: string;
  turn_number: number;
}> {
  const response = await fetch(`${API_URL}/game/${gameId}/status`);
  if (!response.ok) throw new Error('Failed to fetch game status');
  return response.json();
}
