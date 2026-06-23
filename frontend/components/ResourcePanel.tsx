'use client';

import { useGameStore } from '@/store/gameStore';

const resourceEmojis: Record<string, string> = {
  wood: '🌲',
  wheat: '🌾',
  ore: '⛏️',
  brick: '🧱',
  sheep: '🐑',
};

const resourceNames: Record<string, string> = {
  wood: 'Wood',
  wheat: 'Wheat',
  ore: 'Ore',
  brick: 'Brick',
  sheep: 'Sheep',
};

export default function ResourcePanel() {
  const gameState = useGameStore();
  const currentPlayer = gameState.players.find((p) => p.id === gameState.currentPlayerId);

  if (!currentPlayer) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <h3 className="font-semibold mb-3">Resources</h3>
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
      <h3 className="font-semibold mb-3">{currentPlayer.name}'s Resources</h3>
      <div className="space-y-2">
        {Object.entries(currentPlayer.resources).map(([resource, count]) => (
          <div key={resource} className="flex items-center justify-between p-2 bg-slate-700 rounded">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{resourceEmojis[resource]}</span>
              <span className="text-sm">{resourceNames[resource]}</span>
            </div>
            <span className="font-bold text-lg bg-slate-800 px-3 py-1 rounded">{count}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-slate-600">
        <div className="text-sm">
          <div className="flex justify-between mb-2">
            <span>Settlements:</span>
            <span className="font-semibold">{currentPlayer.settlementsCount}</span>
          </div>
          <div className="flex justify-between">
            <span>Roads:</span>
            <span className="font-semibold">{currentPlayer.roadsCount}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
