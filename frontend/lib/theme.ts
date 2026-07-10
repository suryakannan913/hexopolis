/**
 * One icon + one color per concept, used identically everywhere it appears
 * (hex tile, port flag, bank row, hand card, log entry, toolbar).
 */
export const PLAYER_COLORS = ['#5aa0e0', '#e05a5a']; // P0 you (blue), P1 AI (red)

export interface ResourceMeta {
  icon: string;
  hex: string;   // terrain fill on the board
  card: string;  // card/badge background in the HUD
}

export const RESOURCE_META: Record<string, ResourceMeta> = {
  wood:  { icon: '🌲', hex: '#2f6b4f', card: '#2f6b4f' },
  brick: { icon: '🧱', hex: '#b85335', card: '#b85335' },
  sheep: { icon: '🐑', hex: '#7cb98f', card: '#5d9974' },
  wheat: { icon: '🌾', hex: '#e0a82e', card: '#b3861f' },
  ore:   { icon: '⛏️', hex: '#8a93a6', card: '#6b7385' },
};

export const RESOURCE_ORDER = ['wood', 'brick', 'sheep', 'wheat', 'ore'];

export const DESERT = { icon: '🌵', hex: '#cdbd97' };

export function resourceIcon(r: string | null): string {
  return r ? RESOURCE_META[r]?.icon ?? '❓' : DESERT.icon;
}

export function terrainColor(r: string | null): string {
  return r ? RESOURCE_META[r]?.hex ?? '#94a3b8' : DESERT.hex;
}
