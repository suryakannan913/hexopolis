'use client';

import { useState } from 'react';
import type { GameDto, LegalAction } from '@/lib/api';
import { describeAction } from '@/lib/describe';
import type { BoardMode } from '@/components/GameBoard';

interface ToolbarProps {
  game: GameDto;
  mode: BoardMode;
  setMode: (m: BoardMode) => void;
  busy: boolean;
  onAct: (index: number) => void;
}

function Square({ icon, badge, title, onClick, disabled, active, pulse }: {
  icon: string; badge?: number | string; title: string; onClick: () => void;
  disabled?: boolean; active?: boolean; pulse?: boolean;
}) {
  return (
    <button
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`relative flex h-12 w-12 items-center justify-center rounded-lg text-xl transition
        ${active ? 'bg-blue-600 ring-2 ring-blue-300/60' : 'bg-slate-700 hover:bg-slate-600'}
        ${pulse ? 'animate-pulse bg-green-600 hover:bg-green-500' : ''}
        disabled:cursor-not-allowed disabled:opacity-35`}
    >
      {icon}
      {badge !== undefined && (
        <span className="absolute -right-1 -top-1 rounded-full bg-slate-900 px-1.5 text-[10px] font-bold text-slate-200">
          {badge}
        </span>
      )}
    </button>
  );
}

function ChipRow({ actions, busy, onAct, accent }: {
  actions: LegalAction[]; busy: boolean; onAct: (i: number) => void; accent: string;
}) {
  return (
    <div className="flex max-w-xl flex-wrap justify-center gap-1.5">
      {actions.map((a) => (
        <button key={a.index} disabled={busy} onClick={() => onAct(a.index)}
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${accent}
                            disabled:cursor-not-allowed disabled:opacity-40`}>
          {describeAction(a)}
        </button>
      ))}
    </div>
  );
}

/** Bottom-center toolbar: square icon buttons with always-visible supply
 * badges; unaffordable actions dim rather than disappear. */
export default function Toolbar({ game, mode, setMode, busy, onAct }: ToolbarProps) {
  const [tradeOpen, setTradeOpen] = useState(false);
  const me = game.players[0];
  const mine = game.actor === 0 ? game.legal_actions : [];
  const byType = (t: string) => mine.filter((a) => a.type === t);
  const roll = byType('roll')[0];
  const endTurn = byType('end_turn')[0];
  const buyDev = byType('buy_dev_card')[0];
  const trades = byType('maritime_trade');
  const devPlays = mine.filter((a) => a.type.startsWith('play_'));
  const discards = byType('discard');
  const inMain = game.phase === 'main' && game.actor === 0;

  const toggle = (m: Exclude<BoardMode, null>) =>
    setMode(mode === m ? null : m);

  return (
    <div className="relative flex flex-col items-center gap-1.5">
      {tradeOpen && trades.length > 0 && (
        <div className="absolute bottom-full mb-2 rounded-lg border border-slate-600 bg-slate-800 p-2 shadow-xl">
          <ChipRow actions={trades} busy={busy}
                   onAct={(i) => { setTradeOpen(false); onAct(i); }}
                   accent="bg-teal-700 hover:bg-teal-600" />
        </div>
      )}

      {discards.length > 0 && (
        <ChipRow actions={discards} busy={busy} onAct={onAct}
                 accent="bg-rose-700 hover:bg-rose-600" />
      )}
      {devPlays.length > 0 && (
        <ChipRow actions={devPlays} busy={busy} onAct={onAct}
                 accent="bg-purple-700 hover:bg-purple-600" />
      )}

      <div className="flex items-center gap-1.5">
        {roll && (
          <Square icon="🎲" title="Roll the dice" pulse disabled={busy}
                  onClick={() => onAct(roll.index)} />
        )}
        <Square icon="⚖️" title="Bank / port trade"
                disabled={busy || trades.length === 0}
                active={tradeOpen}
                onClick={() => setTradeOpen((v) => !v)} />
        <Square icon="🃏" title="Buy development card" badge={game.dev_deck_remaining}
                disabled={busy || !buyDev}
                onClick={() => buyDev && onAct(buyDev.index)} />
        <Square icon="🛤" title="Build road" badge={me.roads_left}
                disabled={busy || (inMain && byType('build_road').length === 0) || !inMain}
                active={mode === 'road'}
                onClick={() => toggle('road')} />
        <Square icon="🏠" title="Build settlement" badge={me.settlements_left}
                disabled={busy || (inMain && byType('build_settlement').length === 0) || !inMain}
                active={mode === 'settlement'}
                onClick={() => toggle('settlement')} />
        <Square icon="🏰" title="Upgrade to city" badge={me.cities_left}
                disabled={busy || (inMain && byType('build_city').length === 0) || !inMain}
                active={mode === 'city'}
                onClick={() => toggle('city')} />
        <Square icon="✔️" title="End turn"
                disabled={busy || !endTurn}
                onClick={() => endTurn && onAct(endTurn.index)} />
      </div>
    </div>
  );
}
