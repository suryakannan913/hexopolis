'use client';

import type { GameDto } from '@/lib/api';
import { getResourceIcon } from '@/lib/hexUtils';
import { PLAYER_COLORS } from '@/components/GameBoard';

const RESOURCES = ['wood', 'brick', 'sheep', 'wheat', 'ore'];

/** Players, hands, dice, deck — pure display of the server state. */
export default function SidePanel({ game }: { game: GameDto }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-3 space-y-3">
      {game.players.map((p) => {
        const active = game.actor === p.id;
        return (
          <div
            key={p.id}
            className={`rounded p-2 ${active ? 'bg-slate-700/70 ring-1 ring-blue-400/50' : 'bg-slate-700/30'}`}
          >
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 font-medium">
                <span className="inline-block h-3 w-3 rounded-full"
                      style={{ background: PLAYER_COLORS[p.id] }} />
                {p.name}{p.id === 0 && ' (you)'}
              </span>
              <span className="text-lg font-bold text-yellow-400">
                {p.total_vp} <span className="text-xs font-normal text-slate-400">/ 15 VP</span>
              </span>
            </div>
            <div className="mt-1 flex gap-2 text-xs text-slate-400">
              {game.longest_road_owner === p.id && <span className="text-amber-300">🛤 Longest Road</span>}
              {game.largest_army_owner === p.id && <span className="text-amber-300">⚔️ Largest Army</span>}
              <span>⚔️ {p.knights_played}</span>
              <span>🃏 {Object.values(p.dev_cards).reduce((a, b) => a + b, 0)}</span>
            </div>
            <div className="mt-2 grid grid-cols-5 gap-1 text-center text-sm">
              {RESOURCES.map((r) => (
                <div key={r} className="rounded bg-slate-800/80 py-1">
                  <div>{getResourceIcon(r)}</div>
                  <div className="font-semibold">{p.resources[r] ?? 0}</div>
                </div>
              ))}
            </div>
            {p.id === 0 && (
              <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-400">
                {Object.entries(p.dev_cards).filter(([, n]) => n > 0).map(([c, n]) => (
                  <span key={c}>{c.replace(/_/g, ' ')} ×{n}</span>
                ))}
              </div>
            )}
          </div>
        );
      })}

      <div className="flex items-center justify-between text-sm text-slate-300">
        <span>
          🎲 {game.last_roll
            ? `${game.last_roll[0]} + ${game.last_roll[1]} = ${game.last_roll[0] + game.last_roll[1]}`
            : '—'}
        </span>
        <span className="text-slate-400">deck: {game.dev_deck_remaining} 🃏</span>
        <span className="text-slate-400">turn {game.turn_number}</span>
      </div>
    </div>
  );
}
