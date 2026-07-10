import type { Pair } from '@/lib/api';
import { getResourceIcon } from '@/lib/hexUtils';

const ICON = (r: string) => getResourceIcon(r);

function vertexLabel(pairs: Pair[]): string {
  return pairs.map(([q, r]) => `(${q},${r})`).join('·');
}

/** Human-readable label for a legal action / recommendation item. */
export function describeAction(a: { type: string; value: any }): string {
  switch (a.type) {
    case 'roll': return '🎲 Roll dice';
    case 'end_turn': return '⏭ End turn';
    case 'build_settlement': return `🏠 Settlement ${vertexLabel(a.value.vertex)}`;
    case 'build_city': return `🏰 City ${vertexLabel(a.value.vertex)}`;
    case 'build_road': return `🛤 Road ${vertexLabel(a.value.edge)}`;
    case 'buy_dev_card': return '🃏 Buy dev card';
    case 'play_knight': return '⚔️ Play Knight';
    case 'play_road_building': return '🛠 Play Road Building';
    case 'play_year_of_plenty':
      return `🎁 Year of Plenty: ${(a.value as string[]).map(ICON).join(' ') || '—'}`;
    case 'play_monopoly': return `💰 Monopoly: ${ICON(a.value)}`;
    case 'maritime_trade': return `⚖️ Trade ${ICON(a.value[0])} → ${ICON(a.value[1])}`;
    case 'discard': return `🗑 Discard ${ICON(a.value)}`;
    case 'move_robber': return `🦹 Robber → (${a.value.hex[0]},${a.value.hex[1]})`;
    default: return a.type;
  }
}

export function isBoardAction(type: string): boolean {
  return ['build_settlement', 'build_road', 'build_city', 'move_robber'].includes(type);
}
