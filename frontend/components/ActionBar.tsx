'use client';

import type { GameDto, LegalAction } from '@/lib/api';
import { describeAction } from '@/lib/describe';
import type { BoardMode } from '@/components/GameBoard';

interface ActionBarProps {
  game: GameDto;
  mode: BoardMode;
  setMode: (m: BoardMode) => void;
  busy: boolean;
  onAct: (index: number) => void;
}

const PHASE_HELP: Record<string, string> = {
  setup_settlement: '🏠 Opening placement — click a glowing corner for your settlement.',
  setup_road: '🛤 Now place a road on a glowing edge next to it.',
  move_robber: '🦹 You rolled a 7 — click a hex to move the robber.',
  discard: '🗑 Over the 9-card limit — choose cards to discard.',
};

function Btn({ label, onClick, disabled, accent }: {
  label: string; onClick: () => void; disabled?: boolean; accent?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded px-3 py-1.5 text-sm font-medium transition
        ${accent || 'bg-slate-700 hover:bg-slate-600'}
        disabled:cursor-not-allowed disabled:opacity-40`}
    >
      {label}
    </button>
  );
}

/** Everything actionable that isn't a board click, derived from legal_actions. */
export default function ActionBar({ game, mode, setMode, busy, onAct }: ActionBarProps) {
  const mine = game.actor === 0 ? game.legal_actions : [];
  const byType = (t: string): LegalAction[] => mine.filter((a) => a.type === t);
  const one = (t: string): LegalAction | undefined => byType(t)[0];

  const roll = one('roll');
  const endTurn = one('end_turn');
  const buyDev = one('buy_dev_card');
  const devPlays = mine.filter((a) => a.type.startsWith('play_'));
  const trades = byType('maritime_trade');
  const discards = byType('discard');
  const canBuild = {
    settlement: byType('build_settlement').length > 0,
    road: byType('build_road').length > 0,
    city: byType('build_city').length > 0,
  };

  const help = game.winner !== null ? null
    : game.actor !== 0 ? '🤖 Opponent is thinking…'
    : PHASE_HELP[game.phase]
      ?? (roll ? 'Your turn — roll the dice.' : 'Build, trade, play a card, or end your turn.');

  const toggle = (m: Exclude<BoardMode, null>, label: string, enabled: boolean) => (
    <Btn
      key={m}
      label={label}
      disabled={busy || !enabled}
      accent={mode === m ? 'bg-blue-600 hover:bg-blue-500' : undefined}
      onClick={() => setMode(mode === m ? null : m)}
    />
  );

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-3 space-y-2">
      {help && <div className="text-sm text-slate-300">{help}</div>}

      {game.actor === 0 && game.phase === 'discard' && (
        <div className="flex flex-wrap gap-2">
          {discards.map((a) => (
            <Btn key={a.index} label={describeAction(a)} disabled={busy}
                 accent="bg-rose-700 hover:bg-rose-600" onClick={() => onAct(a.index)} />
          ))}
        </div>
      )}

      {game.actor === 0 && game.phase === 'main' && (
        <>
          <div className="flex flex-wrap gap-2">
            {roll && (
              <Btn label="🎲 Roll dice" disabled={busy}
                   accent="bg-green-600 hover:bg-green-500 animate-pulse"
                   onClick={() => onAct(roll.index)} />
            )}
            {toggle('settlement', '🏠 Settlement', canBuild.settlement)}
            {toggle('road', '🛤 Road', canBuild.road)}
            {toggle('city', '🏰 City', canBuild.city)}
            {buyDev && <Btn label="🃏 Buy dev card" disabled={busy} onClick={() => onAct(buyDev.index)} />}
            {endTurn && (
              <Btn label="⏭ End turn" disabled={busy}
                   accent="bg-slate-600 hover:bg-slate-500" onClick={() => onAct(endTurn.index)} />
            )}
          </div>
          {devPlays.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {devPlays.map((a) => (
                <Btn key={a.index} label={describeAction(a)} disabled={busy}
                     accent="bg-purple-700 hover:bg-purple-600 text-xs"
                     onClick={() => onAct(a.index)} />
              ))}
            </div>
          )}
          {trades.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {trades.map((a) => (
                <Btn key={a.index} label={describeAction(a)} disabled={busy}
                     accent="bg-teal-700 hover:bg-teal-600 text-xs"
                     onClick={() => onAct(a.index)} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
