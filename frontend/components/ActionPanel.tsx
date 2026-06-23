'use client';

import { useState } from 'react';
import { useGameStore } from '@/store/gameStore';
import { rollDice, endTurn, executeAITurn } from '@/lib/api';
import BuildPanel from './BuildPanel';

type BuildMode = 'none' | 'settlement' | 'road';

interface ActionPanelProps {
  gameId: string;
  isHumanTurn: boolean;
  onActionComplete: () => void;
  onBuildModeChange?: (mode: BuildMode) => void;
}

export default function ActionPanel({
  gameId,
  isHumanTurn,
  onActionComplete,
  onBuildModeChange,
}: ActionPanelProps) {
  const gameState = useGameStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [buildMode, setBuildMode] = useState<BuildMode>('none');

  const currentPlayer = gameState.players.find((p) => p.id === gameState.currentPlayerId);
  const canAffordSettlement = currentPlayer
    ? currentPlayer.resources.wood >= 1 &&
      currentPlayer.resources.brick >= 1 &&
      currentPlayer.resources.wheat >= 1 &&
      currentPlayer.resources.sheep >= 1
    : false;
  const canAffordRoad =
    currentPlayer &&
    currentPlayer.resources.wood >= 1 &&
    currentPlayer.resources.brick >= 1;

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
      setBuildMode('none');
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

  const handleBuildModeChange = (mode: BuildMode) => {
    setBuildMode(mode);
    onBuildModeChange?.(mode);
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 space-y-4">
      <div>
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
      </div>

      {isHumanTurn && (
        <div className="border-t border-slate-600 pt-4">
          <BuildPanel
            isHumanTurn={isHumanTurn}
            onBuildModeChange={handleBuildModeChange}
            canAffordSettlement={canAffordSettlement}
            canAffordRoad={canAffordRoad}
          />
        </div>
      )}

      <div className="pt-3 border-t border-slate-600">
        <div className="text-xs text-slate-400">
          <p>📝 Dice Roll: {gameState.lastDiceRoll ? `${gameState.lastDiceRoll}` : 'Not rolled'}</p>
          <p>🔄 Turn: {gameState.turnNumber}</p>
        </div>
      </div>
    </div>
  );
}
