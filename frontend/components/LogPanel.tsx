'use client';

import { useEffect, useRef } from 'react';
import type { LogEntry } from '@/lib/gameLog';
import { PLAYER_COLORS, resourceIcon } from '@/lib/theme';

/** Parchment event feed: one line per event, avatar dot + inline icons. */
export default function LogPanel({ log }: { log: LogEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'nearest' });
  }, [log.length]);

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-lg bg-[#f5ecd7] text-slate-900">
      <div className="border-b border-amber-900/15 px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-amber-900/70">
        Game log
      </div>
      <div className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 py-1.5 text-[13px] leading-snug">
        {log.length === 0 && <div className="px-1 py-2 text-amber-900/50">Happy settling!</div>}
        {log.map((e) => (
          <div key={e.id} className="flex items-baseline gap-1.5 rounded px-1 py-0.5">
            {e.player !== null && (
              <span
                className="inline-block h-2.5 w-2.5 shrink-0 self-center rounded-full"
                style={{ background: PLAYER_COLORS[e.player] }}
              />
            )}
            <span>
              <b>{e.player === 0 ? 'You' : e.player === 1 ? 'AI' : ''}</b> {e.text}
              {e.icons?.map((r, i) => <span key={i}> {resourceIcon(r)}</span>)}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
