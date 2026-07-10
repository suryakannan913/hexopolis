import type { GameDto } from '@/lib/api';
import { RESOURCE_ORDER } from '@/lib/theme';

export interface LogEntry {
  id: number;
  player: number | null; // null = neutral/system line
  text: string;
  icons?: string[];      // resource names rendered as inline icons
}

let nextId = 1;
const entry = (player: number | null, text: string, icons?: string[]): LogEntry =>
  ({ id: nextId++, player, text, icons });

const vKey = (v: [number, number][]) => v.map((p) => p.join(',')).join('|');

/**
 * Derive log lines from a state transition. The server has no event stream;
 * everything a turn did is recoverable by diffing consecutive DTOs.
 * `echo` is the human's own action label (known client-side at post time).
 */
export function diffStates(prev: GameDto | null, next: GameDto, echo?: string): LogEntry[] {
  const out: LogEntry[] = [];
  if (!prev) return out;
  const who = prev.actor ?? prev.current_player; // who was deciding before this transition

  if (echo) out.push(entry(0, echo));

  if (next.last_roll && JSON.stringify(next.last_roll) !== JSON.stringify(prev.last_roll)) {
    const [a, b] = next.last_roll;
    out.push(entry(who, `rolled ${a} + ${b} = ${a + b}`));
  }

  // New buildings / roads
  const prevB = new Map(prev.buildings.map((b) => [vKey(b.vertex), b.kind]));
  for (const b of next.buildings) {
    const k = vKey(b.vertex);
    if (!prevB.has(k)) out.push(entry(b.owner, `placed a ${b.kind}`));
    else if (prevB.get(k) !== b.kind) out.push(entry(b.owner, 'upgraded to a city'));
  }
  const prevRoads = [0, 0];
  const nextRoads = [0, 0];
  prev.roads.forEach((r) => prevRoads[r.owner]++);
  next.roads.forEach((r) => nextRoads[r.owner]++);
  for (const pid of [0, 1]) {
    const n = nextRoads[pid] - prevRoads[pid];
    if (n > 0) out.push(entry(pid, n === 1 ? 'placed a road' : `placed ${n} roads`));
  }

  for (const pid of [0, 1]) {
    const dk = next.players[pid].knights_played - prev.players[pid].knights_played;
    if (dk > 0) out.push(entry(pid, 'played a Knight ⚔️'));
    const devDelta =
      Object.values(next.players[pid].dev_cards).reduce((a, b) => a + b, 0) -
      Object.values(prev.players[pid].dev_cards).reduce((a, b) => a + b, 0);
    if (devDelta > 0 && next.dev_deck_remaining < prev.dev_deck_remaining && pid !== 0) {
      out.push(entry(pid, 'bought a development card'));
    }
  }

  if (JSON.stringify(next.robber) !== JSON.stringify(prev.robber)) {
    out.push(entry(who, 'moved the robber 🦹'));
  }

  // Your resource flows (gains always; losses only on the opponent's moves)
  const gained: string[] = [];
  const lost: string[] = [];
  for (const r of RESOURCE_ORDER) {
    const d = (next.players[0].resources[r] ?? 0) - (prev.players[0].resources[r] ?? 0);
    for (let i = 0; i < d; i++) gained.push(r);
    for (let i = 0; i < -d; i++) lost.push(r);
  }
  if (gained.length) out.push(entry(0, 'received', gained));
  if (lost.length && who === 1) out.push(entry(0, 'lost', lost));

  if (next.longest_road_owner !== prev.longest_road_owner && next.longest_road_owner !== null) {
    out.push(entry(next.longest_road_owner, 'took Longest Road 🛤 (+2 VP)'));
  }
  if (next.largest_army_owner !== prev.largest_army_owner && next.largest_army_owner !== null) {
    out.push(entry(next.largest_army_owner, 'took Largest Army ⚔️ (+2 VP)'));
  }
  if (next.winner !== null && prev.winner === null) {
    out.push(entry(next.winner, `wins the game with ${next.players[next.winner].total_vp} VP! 🏆`));
  }
  return out;
}
