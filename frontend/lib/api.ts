/**
 * Client for the action-based engine API.
 *
 * The server is the single source of truth: every response is the full
 * serialized game state, including the indexed `legal_actions` list. The UI
 * never encodes rules — it renders the state and posts an action *index*.
 */
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export type Pair = [number, number];

export interface LegalAction {
  index: number;
  player: number;
  type: string;
  // Shape depends on type: {vertex}, {edge}, {hex}, resource string,
  // [give, receive], resource list, or null.
  value: any;
}

export interface PlayerDto {
  id: number;
  name: string;
  resources: Record<string, number>;
  dev_cards: Record<string, number>;
  knights_played: number;
  roads_left: number;
  settlements_left: number;
  cities_left: number;
  visible_vp: number;
  total_vp: number;
}

export interface GameDto {
  game_id: string;
  seed: number;
  phase: string;
  current_player: number;
  actor: number | null;
  turn_number: number;
  has_rolled: boolean;
  last_roll: [number, number] | null;
  winner: number | null;
  robber: Pair;
  bank: Record<string, number>;
  dev_deck_remaining: number;
  hexes: { q: number; r: number; resource: string | null; number: number | null }[];
  ports: { vertex: Pair[]; type: string }[];
  buildings: { vertex: Pair[]; owner: number; kind: string }[];
  roads: { edge: Pair[]; owner: number }[];
  players: PlayerDto[];
  longest_road_owner: number | null;
  largest_army_owner: number | null;
  legal_actions: LegalAction[];
}

export interface HintItem {
  index: number;
  type: string;
  value: any;
  win_probability?: number;
  score?: number;
  sims?: number;
}

export interface HintsDto {
  game_id: string;
  tier: string;
  advising: number;
  recommendations: HintItem[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      detail = (await response.json()).detail || detail;
    } catch { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return response.json();
}

export function createGame(playerName: string, seed?: number): Promise<GameDto> {
  return request('/game/new', {
    method: 'POST',
    body: JSON.stringify(seed === undefined ? { player_name: playerName }
                                            : { player_name: playerName, seed }),
  });
}

export function getState(gameId: string): Promise<GameDto> {
  return request(`/game/${gameId}`);
}

export function postAction(gameId: string, index: number): Promise<GameDto> {
  return request(`/game/${gameId}/action`, {
    method: 'POST',
    body: JSON.stringify({ index }),
  });
}

export function aiTurn(gameId: string): Promise<GameDto> {
  return request(`/game/${gameId}/ai-turn`, { method: 'POST' });
}

export function getHints(
  gameId: string,
  tier: 'value' | 'alphabeta' | 'mc' | 'mcts',
  opts: { sims?: number; depth?: number; seed?: number } = {},
): Promise<HintsDto> {
  const params = new URLSearchParams({ tier });
  if (opts.sims !== undefined) params.set('sims', String(opts.sims));
  if (opts.depth !== undefined) params.set('depth', String(opts.depth));
  if (opts.seed !== undefined) params.set('seed', String(opts.seed));
  return request(`/game/${gameId}/recommend?${params}`);
}
