'use client';

import type { GameDto } from '@/lib/api';
import { RESOURCE_META, RESOURCE_ORDER } from '@/lib/theme';

/** Bottom-left hand: one small card per resource card, stacked by type,
 * with a count badge per stack — hand size is visually countable. */
export default function HandCards({ game }: { game: GameDto }) {
  const hand = game.players[0].resources;
  const total = RESOURCE_ORDER.reduce((s, r) => s + (hand[r] ?? 0), 0);
  const offset = total > 14 ? 7 : 12; // tighten big hands so they never overflow

  return (
    <div className="flex min-w-0 items-end gap-2 overflow-hidden">
      {RESOURCE_ORDER.map((r) => {
        const n = hand[r] ?? 0;
        if (n === 0) return null;
        return (
          <div key={r} className="relative shrink-0"
               style={{ width: 34 + (n - 1) * offset, height: 48 }}>
            {Array.from({ length: n }).map((_, i) => (
              <div
                key={i}
                className="absolute bottom-0 flex h-12 w-[34px] items-center justify-center rounded-md border border-black/30 text-lg shadow"
                style={{ left: i * offset, background: RESOURCE_META[r].card }}
              >
                {RESOURCE_META[r].icon}
              </div>
            ))}
            <span className="absolute -right-1.5 -top-1.5 z-10 rounded-full bg-slate-900 px-1.5 text-[11px] font-bold">
              {n}
            </span>
          </div>
        );
      })}
      {total === 0 && <span className="pb-3 text-xs text-slate-500">no resource cards</span>}
    </div>
  );
}
