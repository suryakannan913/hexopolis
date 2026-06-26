'use client';

import { useState } from 'react';
import { useGameStore } from '@/store/gameStore';
import { rollDice, endTurn, executeAITurn } from '@/lib/api';
import Toast, { useToast } from './Toast';
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
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [, setBuildMode] = useState<BuildMode>('none');

  const currentPlayer = gameState.players.find((p) => p.id === gameState.currentPlayerId);
  const canAffordSettlement = currentPlayer
    ? currentPlayer.resources.wood >= 1 &&
      currentPlayer.resources.brick >= 1 &&
      currentPlayer.resources.wheat >= 1 &&
      currentPlayer.resources.sheep >= 1
    : false;
  const canAffordRoad = currentPlayer
    ? currentPlayer.resources.wood >= 1 && currentPlayer.resources.brick >= 1
    : false;

  const handleRollDice = async () => {
    setLoading(true);
    try {
      const result = await rollDice(gameId);
      gameState.setGameState({ lastDiceRoll: result.dice_roll });
      toast.success(`🎲 Rolled a ${result.dice_roll}!`);
      onActionComplete();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to roll dice';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleEndTurn = async () => {
    setLoading(true);
    try {
      setBuildMode('none');
      await endTurn(gameId);
      toast.success('✓ Turn ended');
      onActionComplete();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to end turn';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleAITurn = async () => {
    setLoading(true);
    try {
      await executeAITurn(gameId);
      toast.success('✓ AI turn complete');
      onActionComplete();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to execute AI turn';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleBuildModeChange = (mode: BuildMode) => {
    setBuildMode(mode);
    onBuildModeChange?.(mode);
  };

  return (
    <>
      <div className="panel-slide bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-slate-700/50 p-4 space-y-4 shadow-lg">
        <div>
          <h3 className="font-semibold mb-3 text-slate-100">Actions</h3>

          {gameState.status === 'setup' ? (
            <div className="p-3 bg-amber-900/40 border border-amber-700/50 rounded text-amber-100 text-sm">
              🏘️ Place your starting settlements on the board ({gameState.settlements.filter((s) => s.ownerId === 0).length}/2).
            </div>
          ) : gameState.status === 'won' ? (
            <div className="p-3 bg-gradient-to-r from-green-900/60 to-emerald-900/60 border border-green-700/50 rounded text-green-100 text-sm font-semibold settlement-place">
              🎉 Game Over! {gameState.players.find((p) => p.points >= 10)?.name} won!
            </div>
          ) : isHumanTurn ? (
            <div className="space-y-2">
              <button
                onClick={handleRollDice}
                disabled={loading || gameState.lastDiceRoll !== null}
                className="button-hover w-full py-3 px-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 disabled:from-slate-600 disabled:to-slate-700 rounded font-semibold text-sm text-white shadow-md disabled:shadow-none"
              >
                {loading ? (
                  <><span className="spinner"></span> Rolling...</>
                ) : gameState.lastDiceRoll ? (
                  `🎲 Rolled ${gameState.lastDiceRoll}`
                ) : (
                  '🎲 Roll Dice'
                )}
              </button>

              <button
                onClick={handleEndTurn}
                disabled={loading}
                className="button-hover w-full py-3 px-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 disabled:from-slate-600 disabled:to-slate-700 rounded font-semibold text-sm text-white shadow-md disabled:shadow-none"
              >
                {loading ? (
                  <><span className="spinner"></span> Processing...</>
                ) : (
                  '→ End Turn'
                )}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="turn-indicator p-3 bg-slate-700/40 border border-slate-600/50 rounded text-slate-300 text-sm font-medium">
                🤖 AI Opponent's Turn
              </div>
              <button
                onClick={handleAITurn}
                disabled={loading}
                className="button-hover w-full py-3 px-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 disabled:from-slate-600 disabled:to-slate-700 rounded font-semibold text-sm text-white shadow-md disabled:shadow-none"
              >
                {loading ? (
                  <><span className="spinner"></span> Thinking...</>
                ) : (
                  '▶ Execute AI Turn'
                )}
              </button>
            </div>
          )}

          <div className="pt-3 border-t border-slate-600/50 mt-2">
            <div className="text-xs text-slate-400 space-y-1">
              <p>📝 Dice: {gameState.lastDiceRoll ? `${gameState.lastDiceRoll}` : '—'}</p>
              <p>🔄 Turn: {gameState.turnNumber}</p>
            </div>
          </div>
        </div>

        {isHumanTurn && gameState.status === 'in_progress' && (
          <div className="border-t border-slate-600/50 pt-4">
            <BuildPanel
              isHumanTurn={isHumanTurn}
              onBuildModeChange={handleBuildModeChange}
              canAffordSettlement={canAffordSettlement}
              canAffordRoad={canAffordRoad}
            />
          </div>
        )}
      </div>

      <Toast toasts={toast.toasts} onDismiss={toast.dismiss} />
    </>
  );
}
