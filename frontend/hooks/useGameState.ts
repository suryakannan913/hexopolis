import { useEffect, useCallback } from 'react';
import { useGameStore } from '@/store/gameStore';
import { getGameState } from '@/lib/api';

export function useGameState(gameId: string | null, autoRefresh: boolean = true) {
  const { setGameState, setLoading, setError } = useGameStore();

  const fetchGameState = useCallback(async () => {
    if (!gameId) return;

    setLoading(true);
    try {
      const state = await getGameState(gameId);
      setGameState({
        gameId,
        status: state.status as 'setup' | 'in_progress' | 'won',
        currentPlayerId: state.current_player_id,
        currentPlayerName: state.current_player_name,
        turnNumber: state.turn_number,
        lastDiceRoll: state.last_dice_roll,
        players: state.players.map((p) => ({
          id: p.id,
          name: p.name,
          playerType: p.player_type as 'human' | 'ai',
          color: p.color,
          points: p.points,
          resources: {
            wood: p.resources.wood || 0,
            wheat: p.resources.wheat || 0,
            ore: p.resources.ore || 0,
            brick: p.resources.brick || 0,
            sheep: p.resources.sheep || 0,
          },
          settlementsCount: p.settlements_count,
          roadsCount: p.roads_count,
        })),
        settlementsCount: state.settlements_count,
        roadsCount: state.roads_count,
      });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch game state');
    } finally {
      setLoading(false);
    }
  }, [gameId, setGameState, setLoading, setError]);

  // Initial fetch
  useEffect(() => {
    fetchGameState();
  }, [fetchGameState]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || !gameId) return;

    const interval = setInterval(fetchGameState, 2000);
    return () => clearInterval(interval);
  }, [gameId, autoRefresh, fetchGameState]);

  return { fetchGameState };
}
