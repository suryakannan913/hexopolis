'use client';

import { useState } from 'react';
import { useGameStore } from '@/store/gameStore';
import { rollDice, endTurn, executeAITurn } from '@/lib/api';

interface ActionPanelProps {
  gameId: string;
  isHumanTurn: boolean;
  onActionComplete: () => void;
}

export default function ActionPanel({ gameId, isHumanTurn, onActionComplete }: ActionPanelProps) {
  const gameState = useGameStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRollDice = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await rollDice(gameId);
      gameState.setGameState({ lastDiceRoll: result.dice_roll });
      onActionComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to roll dice');
    } finally {
      setLoading(false);
    }
  };

  const handleEndTurn = async () => {
    setLoading(true);
    setError(null);
    try {
      await endTurn(gameId);
      onActionComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to end turn');
    } finally {
      setLoading(false);
    }
  };

  const handleAITurn = async () => {
    setLoading(true);
    setError(null);
    try {
      await executeAITurn(gameId);
      onActionComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute AI turn');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      <h3 className="font-semibold mb-3">Actions</h3>

      {error && <div className="mb-3 p-2 bg-red-900/50 border border-red-700 rounded text-red-200 text-sm">{error}</div>}

      {gameState.status === 'won' ? (
        <div className="p-3 bg-green-900/50 border border-green-700 rounded text-green-200 text-sm font-semibold">
          🎉 Game Over! {gameState.players.find((p) => p.points >= 10)?.name} won!
        </div>
      ) : isHumanTurn ? (
        <div className="space-y-2">
          <button
            onClick={handleRollDice}
            disabled={loading || gameState.lastDiceRoll !== null}
            className="w-full py-2 px-3 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 rounded font-semibold transition text-sm"
          >
            {loading ? '...' : gameState.lastDiceRoll ? `🎲 Rolled ${gameState.lastDiceRoll}` : '🎲 Roll Dice'}
          </button>

          <button
            onClick={handleEndTurn}
            disabled={loading}
            className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 rounded font-semibold transition text-sm"
          >
            {loading ? '...' : 'End Turn'}
          </button>

          <details className="mt-3 text-sm">
            <summary className="font-semibold cursor-pointer text-slate-300">Other Actions (Coming Soon)</summary>
            <div className="mt-2 space-y-2 text-slate-400">
              <button disabled className="w-full py-1 px-2 bg-slate-700 disabled:opacity-50 rounded text-xs">
                🏘️ Build Settlement
              </button>
              <button disabled className="w-full py-1 px-2 bg-slate-700 disabled:opacity-50 rounded text-xs">
                🛣️ Build Road
              </button>
              <button disabled className="w-full py-1 px-2 bg-slate-700 disabled:opacity-50 rounded text-xs">
                💱 Trade Resources
              </button>
            </div>
          </details>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-slate-400">AI Opponent's Turn</p>
          <button
            onClick={handleAITurn}
            disabled={loading}
            className="w-full py-2 px-3 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-600 rounded font-semibold transition text-sm"
          >
            {loading ? '🤖 Thinking...' : '▶ Execute AI Turn'}
          </button>
        </div>
      )}

      <div className="mt-4 pt-3 border-t border-slate-600">
        <div className="text-xs text-slate-400">
          <p>📝 Dice Roll: {gameState.lastDiceRoll ? `${gameState.lastDiceRoll}` : 'Not rolled'}</p>
          <p>🔄 Turn: {gameState.turnNumber}</p>
        </div>
      </div>
    </div>
  );
}
