'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useGame } from '@/hooks/useGame';
import { isBoardAction } from '@/lib/describe';
import GameBoard, { type BoardMode } from '@/components/GameBoard';
import SidePanel from '@/components/SidePanel';
import ActionBar from '@/components/ActionBar';
import HintPanel from '@/components/HintPanel';

export default function GamePage() {
  const params = useParams();
  const gameId = (params?.id as string) || '';
  const { game, busy, analyzing, hints, error, act, analyze, autoHint, setAutoHint } =
    useGame(gameId);
  const [mode, setMode] = useState<BoardMode>(null);

  // Phases with exactly one kind of board interaction force the mode.
  const phase = game?.phase;
  const actor = game?.actor;
  useEffect(() => {
    if (actor !== 0) return setMode(null);
    if (phase === 'setup_settlement') setMode('settlement');
    else if (phase === 'setup_road') setMode('road');
    else if (phase === 'move_robber') setMode('robber');
    else setMode(null);
  }, [phase, actor, game?.turn_number]);

  if (!game) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-xl text-slate-300">{error ? `Error: ${error}` : 'Loading game…'}</div>
      </main>
    );
  }

  const top = hints?.recommendations[0];
  const boardHint = top && isBoardAction(top.type)
    ? { index: top.index, player: 0, type: top.type, value: top.value }
    : null;

  return (
    <main className="flex h-screen flex-col overflow-hidden bg-slate-900 text-white">
      <header className="flex items-center justify-between border-b border-slate-700 bg-slate-800 px-4 py-2">
        <h1 className="text-xl font-bold">Hexopolis <span className="text-sm font-normal text-slate-400">1v1 trainer</span></h1>
        <div className="text-sm text-slate-400">
          seed {game.seed} · turn {game.turn_number} · {game.phase}
          {error && <span className="ml-3 text-rose-400">⚠ {error}</span>}
        </div>
      </header>

      <div className="flex flex-1 gap-3 overflow-hidden p-3">
        <div className="relative flex-1 overflow-hidden rounded-lg border border-slate-700 bg-slate-800">
          <GameBoard
            game={game}
            mode={mode}
            hint={boardHint}
            disabled={busy || game.actor !== 0 || game.winner !== null}
            onPick={act}
          />
          {game.winner !== null && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/70">
              <div className="rounded-xl border border-amber-500/50 bg-slate-800 p-8 text-center">
                <div className="text-3xl font-bold">
                  {game.winner === 0 ? '🎉 You win!' : '🤖 The AI wins.'}
                </div>
                <div className="mt-2 text-slate-300">
                  {game.players[game.winner].total_vp} VP on turn {game.turn_number}
                </div>
                <Link href="/" className="mt-4 inline-block rounded bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500">
                  New game
                </Link>
              </div>
            </div>
          )}
        </div>

        <div className="flex w-96 flex-col gap-3 overflow-y-auto">
          <SidePanel game={game} />
          <ActionBar game={game} mode={mode} setMode={setMode} busy={busy} onAct={act} />
          <HintPanel
            game={game}
            hints={hints}
            analyzing={analyzing}
            autoHint={autoHint}
            setAutoHint={setAutoHint}
            onAnalyze={analyze}
            onAct={act}
            busy={busy}
          />
        </div>
      </div>
    </main>
  );
}
