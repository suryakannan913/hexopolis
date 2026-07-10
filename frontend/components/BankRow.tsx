'use client';

import type { GameDto } from '@/lib/api';
import { RESOURCE_META, RESOURCE_ORDER } from '@/lib/theme';

/** Single-row bank display: remaining supply per resource + dev deck. */
export default function BankRow({ game }: { game: GameDto }) {
  return (
    <div className="flex shrink-0 items-center justify-between rounded-lg bg-[#f5ecd7] px-2 py-1.5">
      <span className="pl-1 text-base" title="Bank">🏛</span>
      {RESOURCE_ORDER.map((r) => (
        <span key={r} className="relative rounded-md px-1.5 py-1 text-lg"
              style={{ background: `${RESOURCE_META[r].card}33` }} title={r}>
          {RESOURCE_META[r].icon}
          <span className="absolute -right-1 -top-1 rounded-full bg-slate-800 px-1 text-[10px] font-bold text-white">
            {game.bank[r] ?? 0}
          </span>
        </span>
      ))}
      <span className="relative rounded-md bg-purple-900/20 px-1.5 py-1 text-lg" title="Dev cards left">
        🃏
        <span className="absolute -right-1 -top-1 rounded-full bg-slate-800 px-1 text-[10px] font-bold text-white">
          {game.dev_deck_remaining}
        </span>
      </span>
    </div>
  );
}
