import { create } from 'zustand';
import type { GameDto, HintsDto } from '@/lib/api';

/** UI state: the latest server DTO plus transient flags. No rules live here. */
interface GameStore {
  game: GameDto | null;
  busy: boolean;           // an action/AI turn is in flight
  analyzing: boolean;      // a hint request is in flight
  hints: HintsDto | null;  // last recommendations for the current state
  error: string | null;

  setGame: (game: GameDto) => void;
  setBusy: (busy: boolean) => void;
  setAnalyzing: (analyzing: boolean) => void;
  setHints: (hints: HintsDto | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useGameStore = create<GameStore>((set) => ({
  game: null,
  busy: false,
  analyzing: false,
  hints: null,
  error: null,

  setGame: (game) => set({ game }),
  setBusy: (busy) => set({ busy }),
  setAnalyzing: (analyzing) => set({ analyzing }),
  setHints: (hints) => set({ hints }),
  setError: (error) => set({ error }),
  reset: () => set({ game: null, busy: false, analyzing: false, hints: null, error: null }),
}));
