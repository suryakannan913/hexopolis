import { useCallback, useEffect, useRef, useState } from 'react';
import { aiTurn, getHints, getState, postAction } from '@/lib/api';
import { describeAction } from '@/lib/describe';
import { diffStates, type LogEntry } from '@/lib/gameLog';
import { useGameStore } from '@/store/gameStore';

/**
 * Orchestrates one game against the server:
 *  - loads state; every POST returns the new full state (no polling)
 *  - after a human action, automatically plays the AI when it's to act
 *  - keeps an event log derived by diffing consecutive states
 *  - fetches instant value-tier hints for the human's decisions (toggleable)
 *  - exposes analyze() for the slower probability tiers on demand
 */
export function useGame(gameId: string) {
  const store = useGameStore();
  const { setGame, setBusy, setAnalyzing, setHints, setError } = store;
  const [autoHint, setAutoHint] = useState(true);
  const [log, setLog] = useState<LogEntry[]>([]);
  const aiPending = useRef(false);

  const applyState = useCallback((next: Parameters<typeof setGame>[0], echo?: string) => {
    const prev = useGameStore.getState().game;
    setLog((l) => [...l, ...diffStates(prev, next, echo)].slice(-120));
    setGame(next);
  }, [setGame]);

  useEffect(() => {
    store.reset();
    setLog([]);
    getState(gameId).then(setGame).catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId]);

  const act = useCallback(async (index: number) => {
    const current = useGameStore.getState();
    if (current.busy) return;
    const action = current.game?.legal_actions.find((a) => a.index === index);
    setBusy(true);
    setHints(null);
    try {
      applyState(await postAction(gameId, index), action ? describeAction(action) : undefined);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'action failed');
    } finally {
      setBusy(false);
    }
  }, [gameId, applyState, setBusy, setError, setHints]);

  // Auto-play the AI whenever the state says it must decide next.
  const { game } = store;
  useEffect(() => {
    if (!game || game.winner !== null || game.actor !== 1 || aiPending.current) return;
    aiPending.current = true;
    setBusy(true);
    const timer = setTimeout(async () => {
      try {
        applyState(await aiTurn(gameId));
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'AI turn failed');
      } finally {
        aiPending.current = false;
        setBusy(false);
      }
    }, 500); // small pause so the handover is visible
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game, gameId]);

  // Instant heuristic hint whenever it's the human's decision.
  useEffect(() => {
    if (!autoHint || !game || game.winner !== null || game.actor !== 0) return;
    if (game.legal_actions.length < 2) return; // forced move: nothing to advise
    let stale = false;
    getHints(gameId, 'value')
      .then((h) => { if (!stale) setHints(h); })
      .catch(() => { /* hints are optional; never block play */ });
    return () => { stale = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game, autoHint, gameId]);

  const analyze = useCallback(async (
    tier: 'value' | 'alphabeta' | 'mc' | 'mcts', sims?: number,
  ) => {
    setAnalyzing(true);
    try {
      setHints(await getHints(gameId, tier, { sims }));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'analysis failed');
    } finally {
      setAnalyzing(false);
    }
  }, [gameId, setAnalyzing, setError, setHints]);

  return { ...store, act, analyze, autoHint, setAutoHint, log };
}
