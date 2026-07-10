'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createGame } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [playerName, setPlayerName] = useState('');
  const [seed, setSeed] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!playerName.trim()) return setError('Please enter your name');
    setLoading(true);
    setError(null);
    try {
      const game = await createGame(playerName.trim(), seed ? Number(seed) : undefined);
      router.push(`/game/${game.game_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create game');
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-900 text-white">
      <div className="w-full max-w-md rounded-lg bg-slate-800 p-8 shadow-lg">
        <h1 className="mb-1 text-center text-4xl font-bold">Hexopolis</h1>
        <p className="mb-8 text-center text-slate-400">
          1v1 Catan trainer — play the AI, get move recommendations with win probabilities
        </p>

        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label htmlFor="name" className="mb-2 block text-sm font-medium">Your name</label>
            <input
              id="name"
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="Enter your name"
              disabled={loading}
              className="w-full rounded border border-slate-600 bg-slate-700 px-4 py-2 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="seed" className="mb-2 block text-sm font-medium">
              Seed <span className="text-slate-400">(optional — reproducible board & dice)</span>
            </label>
            <input
              id="seed"
              type="number"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="random"
              disabled={loading}
              className="w-full rounded border border-slate-600 bg-slate-700 px-4 py-2 focus:border-blue-500 focus:outline-none"
            />
          </div>

          {error && (
            <div className="rounded border border-red-700 bg-red-900/50 p-3 text-red-200">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-blue-600 py-2 font-semibold transition hover:bg-blue-700 disabled:bg-slate-600"
          >
            {loading ? 'Creating game…' : 'Start game vs AI'}
          </button>
        </form>

        <div className="mt-8 rounded border border-slate-600 bg-slate-700/50 p-4 text-sm text-slate-300">
          <h2 className="mb-2 font-semibold">How it works</h2>
          <ul className="space-y-1">
            <li>• Place 2 settlements + roads, then roll, build, and trade</li>
            <li>• First to <b>15 VP</b> wins (cities, roads, army, dev cards)</li>
            <li>• The 🎓 Trainer panel ranks your moves — instant heuristics or Monte Carlo win probabilities</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
