'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createGame } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [playerName, setPlayerName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateGame = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!playerName.trim()) {
      setError('Please enter your name');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { game_id } = await createGame(playerName);
      router.push(`/game/${game_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create game');
      setLoading(false);
    }
  };

  return (
    <main className="flex items-center justify-center min-h-screen">
      <div className="w-full max-w-md p-8 bg-slate-800 rounded-lg shadow-lg">
        <h1 className="text-4xl font-bold text-center mb-2">Hexopolis</h1>
        <p className="text-center text-slate-400 mb-8">A strategy game with hexagonal board and AI opponents</p>

        <form onSubmit={handleCreateGame} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium mb-2">
              Your Name
            </label>
            <input
              id="name"
              type="text"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              placeholder="Enter your name"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded focus:outline-none focus:border-blue-500"
              disabled={loading}
            />
          </div>

          {error && <div className="p-3 bg-red-900/50 border border-red-700 rounded text-red-200">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 rounded font-semibold transition"
          >
            {loading ? 'Creating Game...' : 'Start Game vs AI'}
          </button>
        </form>

        <div className="mt-8 p-4 bg-slate-700/50 border border-slate-600 rounded">
          <h2 className="font-semibold mb-2">How to Play</h2>
          <ul className="text-sm text-slate-300 space-y-1">
            <li>• Roll dice to collect resources</li>
            <li>• Trade resources with the bank</li>
            <li>• Build settlements and roads</li>
            <li>• First to 10 points wins!</li>
          </ul>
        </div>
      </div>
    </main>
  );
}
