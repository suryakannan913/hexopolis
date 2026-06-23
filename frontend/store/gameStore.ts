import { create } from 'zustand';

export interface GameState {
  gameId: string | null;
  status: 'setup' | 'in_progress' | 'won' | null;
  currentPlayerId: number;
  currentPlayerName: string;
  turnNumber: number;
  lastDiceRoll: number | null;
  players: Array<{
    id: number;
    name: string;
    playerType: 'human' | 'ai';
    color: string;
    points: number;
    resources: {
      wood: number;
      wheat: number;
      ore: number;
      brick: number;
      sheep: number;
    };
    settlementsCount: number;
    roadsCount: number;
  }>;
  settlementsCount: number;
  roadsCount: number;
  loading: boolean;
  error: string | null;
}

export interface GameActions {
  setGameId: (gameId: string) => void;
  setGameState: (state: Partial<GameState>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState: Omit<GameState, keyof GameActions> = {
  gameId: null,
  status: null,
  currentPlayerId: 0,
  currentPlayerName: '',
  turnNumber: 0,
  lastDiceRoll: null,
  players: [],
  settlementsCount: 0,
  roadsCount: 0,
  loading: false,
  error: null,
};

export const useGameStore = create<GameState & GameActions>((set) => ({
  ...initialState,
  setGameId: (gameId: string) => set({ gameId }),
  setGameState: (state: Partial<GameState>) => set(state),
  setLoading: (loading: boolean) => set({ loading }),
  setError: (error: string | null) => set({ error }),
  reset: () => set(initialState),
}));
