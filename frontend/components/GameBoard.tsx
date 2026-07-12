'use client';

import type { GameDto, LegalAction, Pair } from '@/lib/api';
import { HEX_RADIUS, hexCorners, hexToPixel, pointsAttr, type PixelCoord } from '@/lib/hexUtils';
import { PLAYER_COLORS, resourceIcon, terrainColor } from '@/lib/theme';

export type BoardMode = 'settlement' | 'road' | 'city' | 'robber' | null;

interface GameBoardProps {
  game: GameDto;
  mode: BoardMode;
  hint: LegalAction | null;   // top recommendation, ringed in gold
  heat?: Record<number, number>; // action index -> 0..1 trainer score (heatmap)
  disabled: boolean;
  onPick: (actionIndex: number) => void;
}

/** Placement-quality color: red (worst) -> green (best). */
function heatColor(t: number, alpha: number): string {
  return `hsla(${Math.round(120 * t)}, 75%, 55%, ${alpha})`;
}

const MODE_TYPES: Record<Exclude<BoardMode, null>, string> = {
  settlement: 'build_settlement',
  road: 'build_road',
  city: 'build_city',
  robber: 'move_robber',
};

const DIRS: Pair[] = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];

function centroid(pairs: Pair[]): PixelCoord {
  const pts = pairs.map(([q, r]) => hexToPixel({ q, r }));
  return {
    x: pts.reduce((s, p) => s + p.x, 0) / pts.length,
    y: pts.reduce((s, p) => s + p.y, 0) / pts.length,
  };
}

/** True endpoints of the edge between two hexes = the two shared corners. */
function edgeEndpoints(edge: Pair[]): [PixelCoord, PixelCoord] {
  const [a, b] = edge;
  const bNeighbors = new Set(DIRS.map((d) => `${b[0] + d[0]},${b[1] + d[1]}`));
  const shared = DIRS.map((d): Pair => [a[0] + d[0], a[1] + d[1]])
    .filter((p) => bNeighbors.has(`${p[0]},${p[1]}`));
  return [centroid([a, b, shared[0]]), centroid([a, b, shared[1]])];
}

/** Anchor point of a board-targeted action (vertex, edge, or hex). */
function actionAnchor(a: { type: string; value: any }): PixelCoord | null {
  if (a.value?.vertex) return centroid(a.value.vertex);
  if (a.value?.edge) {
    const [p1, p2] = edgeEndpoints(a.value.edge);
    return { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
  }
  if (a.value?.hex) return hexToPixel({ q: a.value.hex[0], r: a.value.hex[1] });
  return null;
}

const vKey = (v: Pair[]) => v.map((p) => p.join(',')).join('|');

/** All 54 vertex triples of the board, keyed like the server serializes them. */
function allVertices(game: GameDto): Pair[][] {
  const seen = new Set<string>();
  const out: Pair[][] = [];
  for (const h of game.hexes) {
    for (let i = 0; i < 6; i++) {
      const n1: Pair = [h.q + DIRS[i][0], h.r + DIRS[i][1]];
      const n2: Pair = [h.q + DIRS[(i + 1) % 6][0], h.r + DIRS[(i + 1) % 6][1]];
      const triple = ([[h.q, h.r], n1, n2] as Pair[])
        .slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      const key = vKey(triple);
      if (!seen.has(key)) { seen.add(key); out.push(triple); }
    }
  }
  return out;
}

function Settlement({ at, color }: { at: PixelCoord; color: string }) {
  const s = 11;
  const pts: PixelCoord[] = [
    { x: at.x, y: at.y - s },
    { x: at.x + s * 0.85, y: at.y - s * 0.25 },
    { x: at.x + s * 0.6, y: at.y - s * 0.25 },
    { x: at.x + s * 0.6, y: at.y + s * 0.7 },
    { x: at.x - s * 0.6, y: at.y + s * 0.7 },
    { x: at.x - s * 0.6, y: at.y - s * 0.25 },
    { x: at.x - s * 0.85, y: at.y - s * 0.25 },
  ];
  return <polygon className="piece-pop" points={pointsAttr(pts)} fill={color}
                  stroke="#1e293b" strokeWidth={1.5} />;
}

function City({ at, color }: { at: PixelCoord; color: string }) {
  const p: Pair[] = [
    [-12, 8], [-12, -2], [-4, -2], [-4, -10], [1, -15], [6, -10], [6, -2], [12, -2], [12, 8],
  ];
  return (
    <polygon
      className="piece-pop"
      points={p.map(([dx, dy]) => `${at.x + dx},${at.y + dy}`).join(' ')}
      fill={color} stroke="#1e293b" strokeWidth={1.5}
    />
  );
}

function NumberChip({ at, n }: { at: PixelCoord; n: number }) {
  const hot = n === 6 || n === 8;
  const color = hot ? '#b91c1c' : '#1f2937';
  const pips = 6 - Math.abs(7 - n);
  return (
    <g pointerEvents="none">
      <circle cx={at.x} cy={at.y} r={15} fill="#f5ecd7"
              stroke={hot ? '#b91c1c' : '#9ca3af'} strokeWidth={1.5} />
      <text x={at.x} y={at.y + 1} textAnchor="middle" dominantBaseline="middle"
            fontSize={15} fontWeight={700} fill={color} fontFamily="Georgia, serif">
        {n}
      </text>
      {Array.from({ length: pips }).map((_, i) => (
        <circle key={i} cx={at.x - ((pips - 1) * 3.4) / 2 + i * 3.4} cy={at.y + 9.5}
                r={1.3} fill={color} />
      ))}
    </g>
  );
}

/**
 * The board as pure SVG: the viewBox scales to any container, vertices and
 * edges are real DOM elements (no hand-rolled hit-testing), and pieces
 * animate in with CSS.
 */
export default function GameBoard({ game, mode, hint, heat, disabled, onPick }: GameBoardProps) {
  const centers = game.hexes.map((h) => hexToPixel({ q: h.q, r: h.r }));
  const occupied = new Set(game.buildings.map((b) => vKey(b.vertex)));

  const targets = (mode && !disabled)
    ? game.legal_actions
        .filter((a) => a.type === MODE_TYPES[mode])
        .map((a) => ({ at: actionAnchor(a)!, index: a.index }))
        .filter((t) => t.at)
    : [];
  const hintAt = hint ? actionAnchor(hint) : null;

  return (
    <svg viewBox="-272 -252 544 504" preserveAspectRatio="xMidYMid meet"
         className="h-full w-full" role="img" aria-label="Hexopolis board">
      <defs>
        <radialGradient id="ocean" cx="50%" cy="50%" r="75%">
          <stop offset="0%" stopColor="#1e5b8f" />
          <stop offset="100%" stopColor="#0c2742" />
        </radialGradient>
      </defs>
      <rect x={-272} y={-252} width={544} height={504} fill="url(#ocean)" />

      {/* Shore glow + sandy coastline */}
      {centers.map((c, i) => (
        <polygon key={`g${i}`} points={pointsAttr(hexCorners(c, HEX_RADIUS * 1.62))}
                 fill="rgba(120,190,230,0.18)" />
      ))}
      {centers.map((c, i) => (
        <polygon key={`s${i}`} points={pointsAttr(hexCorners(c, HEX_RADIUS * 1.3))} fill="#e8d5a3" />
      ))}
      {centers.map((c, i) => (
        <polygon key={`t${i}`} points={pointsAttr(hexCorners(c, HEX_RADIUS * 1.22))} fill="#d9c08a" />
      ))}

      {/* Terrain hexes with icon + number token */}
      {game.hexes.map((h, i) => {
        const c = centers[i];
        return (
          <g key={`${h.q},${h.r}`}>
            <polygon points={pointsAttr(hexCorners(c))} fill={terrainColor(h.resource)}
                     stroke="rgba(15,23,42,0.45)" strokeWidth={2} />
            <text x={c.x} y={c.y - 16} textAnchor="middle" dominantBaseline="middle"
                  fontSize={19} pointerEvents="none">
              {resourceIcon(h.resource)}
            </text>
            {h.number !== null && <NumberChip at={{ x: c.x, y: c.y + 13 }} n={h.number} />}
            {h.q === game.robber[0] && h.r === game.robber[1] && (
              <g pointerEvents="none" className="piece-pop">
                <circle cx={c.x - 22} cy={c.y - 2} r={11} fill="rgba(30,41,59,0.92)" />
                <text x={c.x - 22} y={c.y - 1} textAnchor="middle" dominantBaseline="middle"
                      fontSize={12} fontWeight={700} fill="#f8fafc">R</text>
              </g>
            )}
          </g>
        );
      })}

      {/* Ports: boat offshore, ratio badge, tie-line to the vertex */}
      {game.ports.map((port, i) => {
        const v = centroid(port.vertex);
        const len = Math.hypot(v.x, v.y) || 1;
        const bx = v.x + (v.x / len) * 30;
        const by = v.y + (v.y / len) * 30;
        const label = port.type === '3:1' ? '3:1 ?' : `2:1 ${resourceIcon(port.type)}`;
        return (
          <g key={`p${i}`} pointerEvents="none">
            <line x1={v.x} y1={v.y} x2={bx} y2={by - 2} stroke="rgba(248,250,252,0.35)" />
            <text x={bx} y={by - 8} textAnchor="middle" fontSize={15}>⛵</text>
            <rect x={bx - 21} y={by + 2} width={42} height={14} rx={5}
                  fill="rgba(248,250,252,0.92)" />
            <text x={bx} y={by + 9.5} textAnchor="middle" dominantBaseline="middle"
                  fontSize={9} fontWeight={700} fill="#0f172a">{label}</text>
          </g>
        );
      })}

      {/* Open building spots — always faintly visible */}
      {allVertices(game).map((triple) => {
        const key = vKey(triple);
        if (occupied.has(key)) return null;
        const v = centroid(triple);
        return <circle key={key} cx={v.x} cy={v.y} r={3} fill="rgba(248,250,252,0.18)"
                       pointerEvents="none" />;
      })}

      {/* Roads (dark outline under color), then buildings on top */}
      {game.roads.map((r) => {
        const [p1, p2] = edgeEndpoints(r.edge);
        const key = r.edge.map((p) => p.join(',')).join('|');
        return (
          <g key={key} className="piece-pop">
            <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#1e293b"
                  strokeWidth={10} strokeLinecap="round" />
            <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke={PLAYER_COLORS[r.owner]}
                  strokeWidth={7} strokeLinecap="round" />
          </g>
        );
      })}
      {game.buildings.map((b) => {
        const at = centroid(b.vertex);
        return b.kind === 'city'
          ? <City key={vKey(b.vertex)} at={at} color={PLAYER_COLORS[b.owner]} />
          : <Settlement key={vKey(b.vertex)} at={at} color={PLAYER_COLORS[b.owner]} />;
      })}

      {/* Clickable targets for the active mode; heat-colored when the trainer
          has scored the options (green = its preference, red = weakest) */}
      {targets.map((t) => {
        const h = heat?.[t.index];
        const fill = h === undefined ? 'rgba(134,239,172,0.22)' : heatColor(h, 0.4);
        const ring = h === undefined ? 'rgba(187,247,208,0.9)' : heatColor(h, 0.95);
        return (
          <g key={t.index} className="board-target cursor-pointer" onClick={() => onPick(t.index)}>
            <circle cx={t.at.x} cy={t.at.y} r={16} fill="transparent" />
            <circle className="target-pulse" cx={t.at.x} cy={t.at.y} r={13}
                    fill={fill} pointerEvents="none" />
            <circle className="target-ring" cx={t.at.x} cy={t.at.y} r={8} fill="none"
                    stroke={ring} strokeWidth={2} pointerEvents="none" />
          </g>
        );
      })}

      {/* Gold ring on the trainer's top recommendation */}
      {hintAt && (
        <circle className="hint-ring" cx={hintAt.x} cy={hintAt.y} r={17} fill="none"
                stroke="#fbbf24" strokeWidth={3} strokeDasharray="6 4" pointerEvents="none" />
      )}
    </svg>
  );
}
