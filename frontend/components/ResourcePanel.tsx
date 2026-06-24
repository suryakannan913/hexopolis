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
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-slate-700/50 p-4">
        <h3 className="font-semibold mb-3">Resources</h3>
        <p className="text-slate-400">Loading...</p>
      </div>
    );
  }

  return (
    <div className="panel-slide bg-gradient-to-br from-slate-800 to-slate-900 rounded-lg border border-slate-700/50 p-4 shadow-lg">
      <h3 className="font-semibold mb-3 text-slate-100">{currentPlayer.name}'s Resources</h3>
      <div className="space-y-2">
        {Object.entries(currentPlayer.resources).map(([resource, count]) => (
          <div
            key={resource}
            className="flex items-center justify-between p-2 bg-slate-700/40 hover:bg-slate-700/60 rounded smooth-transition group"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl group-hover:scale-110 smooth-transition">{resourceEmojis[resource]}</span>
              <span className="text-sm text-slate-300">{resourceNames[resource]}</span>
            </div>
            <span className="font-bold text-lg bg-slate-800/60 px-3 py-1 rounded resource-change">{count}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 border-t border-slate-600/50">
        <div className="text-sm text-slate-300 space-y-2">
          <div className="flex justify-between group">
            <span className="group-hover:text-slate-100 smooth-transition">🏘️ Settlements:</span>
            <span className="font-semibold text-slate-100">{currentPlayer.settlementsCount}</span>
          </div>
          <div className="flex justify-between group">
            <span className="group-hover:text-slate-100 smooth-transition">🛣️ Roads:</span>
            <span className="font-semibold text-slate-100">{currentPlayer.roadsCount}</span>
          </div>
          <div className="flex justify-between group">
            <span className="group-hover:text-slate-100 smooth-transition">⭐ Points:</span>
            <span className="font-semibold text-yellow-400">{currentPlayer.points}/10</span>
          </div>
        </div>
      </div>
    </div>
  );
}
