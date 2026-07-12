'use client';

import type { GameDto } from '@/lib/api';

/** Top-center one-line imperative prompt — the only instructional text. */
export default function PromptBar({ game, error }: { game: GameDto; error: string | null }) {
  let prompt: string;
  if (game.winner !== null) prompt = game.winner === 0 ? '🏆 You win!' : '🤖 The AI wins';
  else if (game.actor !== 0) prompt = "Opponent's turn…";
  else if (game.phase === 'setup_settlement') prompt = 'Place a settlement';
  else if (game.phase === 'setup_road') prompt = 'Place a road';
  else if (game.phase === 'move_robber') prompt = 'Move the robber';
  else if (game.phase === 'discard') prompt = `Discard ${game.discard_quota[0]} more cards`;
  else if (game.legal_actions.some((a) => a.type === 'roll')) prompt = 'Roll the dice';
  else prompt = 'Build, trade, or end turn';

  return (
    <header className="flex h-11 shrink-0 items-center border-b border-slate-700 bg-slate-800 px-4">
      <div className="w-48 text-sm font-bold">
        Hexopolis <span className="font-normal text-slate-500">trainer</span>
      </div>
      <div className="flex-1 text-center">
        <span className="rounded-full bg-slate-700/80 px-4 py-1 text-sm font-semibold tracking-wide">
          {prompt}
        </span>
      </div>
      <div className="w-48 text-right text-xs text-slate-500">
        {error ? <span className="text-rose-400">⚠ {error}</span>
               : <>seed {game.seed} · turn {game.turn_number}</>}
      </div>
    </header>
  );
}
