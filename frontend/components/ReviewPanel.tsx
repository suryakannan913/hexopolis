'use client';

import { useEffect, useState } from 'react';
import { getReview, type ReviewDto } from '@/lib/api';
import { describeAction } from '@/lib/describe';

/** Post-game review: how each of your decisions ranked against the trainer. */
export default function ReviewPanel({ gameId, onClose }: { gameId: string; onClose: () => void }) {
  const [review, setReview] = useState<ReviewDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReview(gameId).then(setReview).catch((e) => setError(e.message));
  }, [gameId]);

  const badge = (rank: number | null) => {
    if (rank === 1) return <span className="rounded bg-green-700 px-1.5 text-[10px] font-bold">BEST</span>;
    if (rank !== null && rank <= 3) return <span className="rounded bg-slate-600 px-1.5 text-[10px] font-bold">OK</span>;
    return <span className="rounded bg-rose-700 px-1.5 text-[10px] font-bold">WEAK</span>;
  };

  const worstFirst = review
    ? [...review.decisions].sort((a, b) => (b.rank ?? 0) - (a.rank ?? 0))
    : [];

  return (
    <div className="flex max-h-[70vh] w-[30rem] flex-col rounded-xl border border-amber-500/50 bg-slate-800 p-5 text-left">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-lg font-bold">🎓 Game review</h3>
        <button onClick={onClose} className="rounded bg-slate-700 px-2 py-0.5 text-sm hover:bg-slate-600">✕</button>
      </div>

      {error && <div className="text-sm text-rose-400">⚠ {error}</div>}
      {!review && !error && <div className="text-sm text-slate-400">Analyzing your decisions…</div>}

      {review && (
        <>
          <div className="mb-3 flex gap-4 text-sm">
            <span className="text-green-400">✓ best: {review.summary.best}</span>
            <span className="text-slate-300">~ fine: {review.summary.fine}</span>
            <span className="text-rose-400">✗ weak: {review.summary.weak}</span>
            <span className="ml-auto text-slate-400">{review.summary.total} decisions</span>
          </div>
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto pr-1 text-sm">
            {worstFirst.map((d) => (
              <div key={d.ply} className="rounded bg-slate-700/50 px-2 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">turn {d.turn}</span>
                  {badge(d.rank)}
                  <span className="ml-auto text-xs text-slate-400">
                    ranked {d.rank ?? '—'}/{d.n_options}
                  </span>
                </div>
                <div className="truncate">{describeAction(d.chosen)}</div>
                {d.rank !== null && d.rank > 1 && (
                  <div className="truncate text-xs text-amber-300">
                    trainer preferred: {describeAction(d.best)}
                  </div>
                )}
              </div>
            ))}
            {review.decisions.length === 0 && (
              <div className="text-slate-400">No multi-option decisions to review yet.</div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
