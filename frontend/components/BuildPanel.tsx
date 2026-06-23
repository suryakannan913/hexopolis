'use client';

import { useState } from 'react';

type BuildMode = 'none' | 'settlement' | 'road';

interface BuildPanelProps {
  isHumanTurn: boolean;
  onBuildModeChange: (mode: BuildMode) => void;
  canAffordSettlement: boolean;
  canAffordRoad: boolean;
}

export default function BuildPanel({
  isHumanTurn,
  onBuildModeChange,
  canAffordSettlement,
  canAffordRoad,
}: BuildPanelProps) {
  const [buildMode, setBuildMode] = useState<BuildMode>('none');

  const handleSelectMode = (mode: BuildMode) => {
    const newMode = buildMode === mode ? 'none' : mode;
    setBuildMode(newMode);
    onBuildModeChange(newMode);
  };

  if (!isHumanTurn) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
        <p className="text-sm text-slate-400">Waiting for opponent...</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 space-y-3">
      <h3 className="font-semibold text-sm">Build Mode</h3>

      <div className="space-y-2">
        <button
          onClick={() => handleSelectMode('settlement')}
          disabled={!canAffordSettlement}
          className={`w-full py-2 px-3 rounded font-semibold transition text-sm ${
            buildMode === 'settlement'
              ? 'bg-blue-600 text-white'
              : canAffordSettlement
                ? 'bg-slate-700 hover:bg-slate-600 text-slate-200'
                : 'bg-slate-700 text-slate-500 cursor-not-allowed opacity-50'
          }`}
        >
          {buildMode === 'settlement' ? '✓ ' : ''}🏘️ Settlement
          {!canAffordSettlement && ' (Not enough resources)'}
        </button>

        <button
          onClick={() => handleSelectMode('road')}
          disabled={!canAffordRoad}
          className={`w-full py-2 px-3 rounded font-semibold transition text-sm ${
            buildMode === 'road'
              ? 'bg-blue-600 text-white'
              : canAffordRoad
                ? 'bg-slate-700 hover:bg-slate-600 text-slate-200'
                : 'bg-slate-700 text-slate-500 cursor-not-allowed opacity-50'
          }`}
        >
          {buildMode === 'road' ? '✓ ' : ''}🛣️ Road
          {!canAffordRoad && ' (Not enough resources)'}
        </button>
      </div>

      {buildMode !== 'none' && (
        <div className="p-3 bg-blue-900/30 border border-blue-700/50 rounded text-sm text-blue-200">
          {buildMode === 'settlement' && 'Click on a hex vertex to place a settlement'}
          {buildMode === 'road' && 'Click on an edge between hexes to build a road'}
        </div>
      )}

      <button
        onClick={() => handleSelectMode('none')}
        className="w-full py-2 px-3 bg-slate-700 hover:bg-slate-600 rounded font-semibold transition text-sm text-slate-200"
      >
        Cancel
      </button>

      <div className="pt-3 border-t border-slate-600 text-xs text-slate-400 space-y-1">
        <div>🏘️ Settlement: Wood, Brick, Wheat, Sheep</div>
        <div>🛣️ Road: Wood, Brick</div>
      </div>
    </div>
  );
}
