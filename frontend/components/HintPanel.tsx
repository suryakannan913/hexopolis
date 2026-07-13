'use client';

import { useState } from 'react';
import type { GameDto, HintsDto } from '@/lib/api';
import { describeAction } from '@/lib/describe';

interface HintPanelProps {
  game: GameDto;
  hints: HintsDto | null;
  analyzing: boolean;
  autoHint: boolean;
  setAutoHint: (v: boolean) => void;
  onAnalyze: (tier: 'value' | 'alphabeta' | 'mc' | 'mcts', sims?: number) => void;
  onAct: (index: number) => void;
  busy: boolean;
}

const TIERS = [
  { id: 'value', label: 'Value', title: 'Instant heuristic (1-ply value function)' },
  { id: 'alphabeta', label: 'Search', title: 'Expectiminimax, depth 2' },
  { id: 'mc', label: 'Monte Carlo', title: '25 rollouts per action — win probabilities (~10s)' },
  { id: 'mcts', label: 'MCTS', title: '200 UCB1 simulations — win probabilities (~10s)' },
] as const;

function metric(x: { win_probability?: number; score?: number; sims?: number }): string {
  if (x.win_probability !== undefined) return `${(x.win_probability * 100).toFixed(0)}%`;
  if (x.score !== undefined) return x.score.toExponential(2);
  return '';
}

/** The trainer: rank the current position's moves on demand. */
export default function HintPanel(props: HintPanelProps) {
  const { game, hints, analyzing, autoHint, setAutoHint, onAnalyze, onAct, busy } = props;
  const [tier, setTier] = useState<(typeof TIERS)[number]['id']>('value');
  const stale = hints === null;
  const showProb = hints?.tier === 'mc' || hints?.tier === 'mcts';

  return (
    <div className="shrink-0 rounded-lg border border-slate-700 bg-slate-800 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-100">🎓 Trainer</h3>
        <label className="flex items-center gap-1.5 text-xs text-slate-400">
          <input type="checkbox" checked={autoHint} onChange={(e) => setAutoHint(e.target.checked)} />
          auto-hint
        </label>
      </div>

      <div className="flex gap-1.5">
        {TIERS.map((t) => (
          <button
            key={t.id}
            title={t.title}
            onClick={() => setTier(t.id)}
            className={`rounded px-2 py-1 text-xs ${tier === t.id
              ? 'bg-amber-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
          >
            {t.label}
          </button>
        ))}
        <button
          onClick={() => onAnalyze(tier)}
          disabled={analyzing || game.actor !== 0 || game.winner !== null}
          className="ml-auto rounded bg-amber-700 px-3 py-1 text-xs font-medium hover:bg-amber-600
                     disabled:cursor-not-allowed disabled:opacity-40"
        >
          {analyzing ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      {hints && (
        <div className="space-y-1">
          <div className="text-xs text-slate-400">
            {hints.tier} tier{showProb ? ' — estimated win probability' : ' — heuristic score'}
          </div>
          {hints.recommendations.slice(0, 6).map((r, i) => (
            <div
              key={r.index}
              className={`flex items-center gap-2 rounded px-2 py-1 text-sm
                ${i === 0 ? 'bg-amber-900/40 ring-1 ring-amber-500/40' : 'bg-slate-700/40'}`}
            >
              <span className="w-4 text-right text-xs text-slate-400">{i + 1}</span>
              <span className="flex-1 truncate">{describeAction(r)}</span>
              <span className={`text-xs font-semibold ${i === 0 ? 'text-amber-300' : 'text-slate-300'}`}>
                {metric(r)}
              </span>
              <button
                onClick={() => onAct(r.index)}
                disabled={busy || game.actor !== 0}
                className="rounded bg-slate-600 px-2 py-0.5 text-xs hover:bg-slate-500
                           disabled:cursor-not-allowed disabled:opacity-40"
              >
                play
              </button>
            </div>
          ))}
        </div>
      )}
      {stale && !analyzing && game.actor === 0 && game.winner === null && (
        <div className="text-xs text-slate-500">
          Pick a tier and hit Analyze — Monte Carlo tiers take ~10s but return win probabilities.
        </div>
      )}
    </div>
  );
}
