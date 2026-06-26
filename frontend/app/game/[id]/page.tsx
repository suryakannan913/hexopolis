'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useGameStore } from '@/store/gameStore';
import { useGameState } from '@/hooks/useGameState';
import GameBoard from '@/components/GameBoard';
import ResourcePanel from '@/components/ResourcePanel';
import ActionPanel from '@/components/ActionPanel';

type BuildMode = 'none' | 'settlement' | 'road';

export default function GamePage() {
  const params = useParams();
  const gameId = (params?.id as string) || '';
  const gameState = useGameStore();
  const { fetchGameState } = useGameState(gameId);
  const [buildMode, setBuildMode] = useState<BuildMode>('none');

  const isSetup = gameState.status === 'setup';
  const humanSettlements = gameState.settlements.filter((s) => s.ownerId === 0).length;

  // During the opening phase, the only action is placing settlements.
  // Once it ends, clear the mode so normal play starts from a clean slate.
  useEffect(() => {
    setBuildMode(isSetup ? 'settlement' : 'none');
  }, [isSetup]);

  if (gameState.loading && !gameState.gameId) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="text-2xl">Loading game...</div>
      </main>
    );
  }

  if (gameState.error) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <div className="text-2xl text-red-500">Error: {gameState.error}</div>
      </main>
    );
  }

  const currentPlayer = gameState.players.find((p) => p.id === gameState.currentPlayerId);
  const isHumanTurn = currentPlayer?.playerType === 'human';

  return (
    <main className="w-full h-screen bg-slate-900 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 p-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Hexopolis</h1>
          <div className="text-sm text-slate-400">
            Turn {gameState.turnNumber} • {gameState.status === 'won' ? '🎉 Game Won!' : `${currentPlayer?.name}'s Turn`}
          </div>
        </div>
      </header>

      {/* Setup banner */}
      {isSetup && (
        <div className="bg-amber-900/40 border-b border-amber-700/50 px-4 py-2 text-amber-100 text-sm text-center">
          🏘️ Opening placement — click the board to place your starting settlements ({humanSettlements}/2). They grant your starting resources.
        </div>
      )}

      {/* Game Container */}
      <div className="flex flex-1 overflow-hidden gap-4 p-4">
        {/* Left: Game Board */}
        <div className="flex-1 bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <GameBoard gameId={gameId} buildMode={buildMode} onBuildModeChange={setBuildMode} onActionComplete={fetchGameState} />
        </div>

        {/* Right Sidebar */}
        <div className="w-80 flex flex-col gap-4">
          {/* Resource Panel */}
          <ResourcePanel />

          {/* Action Panel */}
          <ActionPanel gameId={gameId} isHumanTurn={isHumanTurn} onActionComplete={fetchGameState} onBuildModeChange={setBuildMode} />

          {/* Players Info */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 flex-1 overflow-y-auto">
            <h3 className="font-semibold mb-3">Players</h3>
            <div className="space-y-2">
              {gameState.players.map((player) => (
                <div
                  key={player.id}
                  className={`p-2 rounded ${player.id === gameState.currentPlayerId ? 'bg-blue-900/50 border-l-2 border-blue-500' : 'bg-slate-700'}`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-medium">{player.name}</span>
                    <span className="text-lg font-bold text-yellow-400">{player.points} pts</span>
                  </div>
                  <div className="text-sm text-slate-400">
                    {player.settlementsCount} settlements • {player.roadsCount} roads
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
