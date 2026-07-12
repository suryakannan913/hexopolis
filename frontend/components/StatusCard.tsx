'use client';

import type { GameDto } from '@/lib/api';
import { PLAYER_COLORS } from '@/lib/theme';

/** Bottom-right: compact status card per player — avatar, VP banner, badges. */
function OnePlayer({ game, pid }: { game: GameDto; pid: number }) {
  const p = game.players[pid];
  const active = game.actor === pid && game.winner === null;
  const devs = Object.values(p.dev_cards).reduce((a, b) => a + b, 0);
  return (
    <div className={`flex items-center gap-2.5 rounded-lg border px-2.5 py-1.5
      ${active ? 'border-amber-400/60 bg-slate-700/80' : 'border-slate-700 bg-slate-800'}`}>
      <span className="w-3 text-amber-300">{active ? '▶' : ''}</span>
      <span
        className="flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold text-white"
        style={{ background: PLAYER_COLORS[pid] }}
      >
        {p.name[0]?.toUpperCase()}
      </span>
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold leading-tight">
          {p.name}{pid === 0 && <span className="text-slate-400"> (you)</span>}
        </div>
        <div className="flex gap-2.5 text-[11px] text-slate-400">
          <span title="Hidden dev cards">🃏 {devs}</span>
          <span title="Knights played">⚔️ {p.knights_played}</span>
          <span title="Longest road length">🛤 {p.longest_road}</span>
          {game.longest_road_owner === pid && <span className="text-amber-300" title="Longest Road">🛤+2</span>}
          {game.largest_army_owner === pid && <span className="text-amber-300" title="Largest Army">⚔️+2</span>}
        </div>
      </div>
      <div className="ml-1 rounded-md bg-slate-900/80 px-2 py-1 text-center">
        <div className="text-base font-bold leading-none text-yellow-400">{p.total_vp}</div>
        <div className="text-[9px] text-slate-500">/15 VP</div>
      </div>
    </div>
  );
}

export default function StatusCard({ game }: { game: GameDto }) {
  return (
    <div className="flex min-w-0 justify-end gap-2">
      <OnePlayer game={game} pid={1} />
      <OnePlayer game={game} pid={0} />
    </div>
  );
}
