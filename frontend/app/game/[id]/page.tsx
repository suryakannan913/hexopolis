'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useGame } from '@/hooks/useGame';
import { isBoardAction } from '@/lib/describe';
import GameBoard, { type BoardMode } from '@/components/GameBoard';
import PromptBar from '@/components/PromptBar';
import LogPanel from '@/components/LogPanel';
import BankRow from '@/components/BankRow';
import HandCards from '@/components/HandCards';
import Toolbar from '@/components/Toolbar';
import StatusCard from '@/components/StatusCard';
import HintPanel from '@/components/HintPanel';
import ReviewPanel from '@/components/ReviewPanel';

export default function GamePage() {
  const params = useParams();
  const gameId = (params?.id as string) || '';
  const { game, busy, analyzing, hints, error, act, analyze, autoHint, setAutoHint, log } =
    useGame(gameId);
  const [mode, setMode] = useState<BoardMode>(null);
  const [showReview, setShowReview] = useState(false);

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
      <main className="flex min-h-screen items-center justify-center bg-slate-900 text-slate-300">
        {error ? `Error: ${error}` : 'Loading game…'}
      </main>
    );
  }

  const top = hints?.recommendations[0];
  const boardHint = top && isBoardAction(top.type)
    ? { index: top.index, player: 0, type: top.type, value: top.value }
    : null;

  // Placement heatmap: normalize the trainer's scores over the board-targeted
  // options so target circles shade red (weak) -> green (trainer's pick).
  let heat: Record<number, number> | undefined;
  const scored = hints?.recommendations.filter(
    (r) => isBoardAction(r.type) && (r.score !== undefined || r.win_probability !== undefined));
  if (scored && scored.length >= 2) {
    const vals = scored.map((r) => r.score ?? r.win_probability ?? 0);
    const lo = Math.min(...vals);
    const span = Math.max(...vals) - lo || 1;
    heat = Object.fromEntries(scored.map((r, i) => [r.index, (vals[i] - lo) / span]));
  }

  return (
    <main className="flex h-screen flex-col overflow-hidden bg-slate-900 text-white">
      <PromptBar game={game} error={error} />

      {/* Center: board anchor + fixed-width right rail (log, bank, trainer) */}
      <div className="flex min-h-0 flex-1 gap-2 p-2">
        <div className="relative min-w-0 flex-1 overflow-hidden rounded-lg border border-slate-700">
          <GameBoard
            game={game}
            mode={mode}
            hint={boardHint}
            heat={heat}
            disabled={busy || game.actor !== 0 || game.winner !== null}
            onPick={act}
          />
          {game.winner !== null && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-950/70">
              {showReview ? (
                <ReviewPanel gameId={gameId} onClose={() => setShowReview(false)} />
              ) : (
                <div className="rounded-xl border border-amber-500/50 bg-slate-800 p-8 text-center">
                  <div className="text-3xl font-bold">
                    {game.winner === 0 ? '🎉 You win!' : '🤖 The AI wins.'}
                  </div>
                  <div className="mt-2 text-slate-300">
                    {game.players[game.winner].total_vp} VP on turn {game.turn_number}
                  </div>
                  <div className="mt-4 flex justify-center gap-2">
                    <button
                      onClick={() => setShowReview(true)}
                      className="rounded bg-amber-600 px-4 py-2 font-medium hover:bg-amber-500"
                    >
                      🎓 Review game
                    </button>
                    <Link href="/" className="inline-block rounded bg-blue-600 px-4 py-2 font-medium hover:bg-blue-500">
                      New game
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Fixed-width rail: never reshapes — it scrolls when content grows */}
        <aside className="flex w-80 shrink-0 flex-col gap-2 overflow-y-auto overflow-x-hidden">
          <LogPanel log={log} />
          <BankRow game={game} />
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
        </aside>
      </div>

      {/* Bottom: hand | toolbar | player status. Fixed height so contextual
          chip rows (rendered as overlays) never resize the board above. */}
      <footer className="grid h-24 shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-3 px-3">
        <HandCards game={game} />
        <Toolbar game={game} mode={mode} setMode={setMode} busy={busy} onAct={act} />
        <StatusCard game={game} />
      </footer>
    </main>
  );
}
