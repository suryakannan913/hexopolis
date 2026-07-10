'use client';

import { useEffect, useRef, useState } from 'react';
import type { GameDto, LegalAction, Pair } from '@/lib/api';
import {
  HEX_RADIUS,
  drawHex,
  drawNumberChip,
  drawRoad,
  drawSettlement,
  fillHexShape,
  getResourceColor,
  getResourceIcon,
  hexToPixel,
  type PixelCoord,
} from '@/lib/hexUtils';

export const PLAYER_COLORS = ['#5aa0e0', '#e05a5a']; // P0 you, P1 AI

export type BoardMode = 'settlement' | 'road' | 'city' | 'robber' | null;

interface GameBoardProps {
  game: GameDto;
  mode: BoardMode;
  hint: LegalAction | null;   // top recommendation, highlighted in gold
  disabled: boolean;
  onPick: (actionIndex: number) => void;
}

const MODE_TYPES: Record<Exclude<BoardMode, null>, string> = {
  settlement: 'build_settlement',
  road: 'build_road',
  city: 'build_city',
  robber: 'move_robber',
};

const DIRS: Pair[] = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];

interface Target { x: number; y: number; index: number }

function centroid(pairs: Pair[], ox: number, oy: number): PixelCoord {
  const pts = pairs.map(([q, r]) => hexToPixel({ q, r }, ox, oy));
  return {
    x: pts.reduce((s, p) => s + p.x, 0) / pts.length,
    y: pts.reduce((s, p) => s + p.y, 0) / pts.length,
  };
}

/** True endpoints of the edge between two hexes = the two shared corners. */
function edgeEndpoints(edge: Pair[], ox: number, oy: number): [PixelCoord, PixelCoord] {
  const [a, b] = edge;
  const bNeighbors = new Set(DIRS.map((d) => `${b[0] + d[0]},${b[1] + d[1]}`));
  const shared = DIRS.map((d): Pair => [a[0] + d[0], a[1] + d[1]])
    .filter((p) => bNeighbors.has(`${p[0]},${p[1]}`));
  return [centroid([a, b, shared[0]], ox, oy), centroid([a, b, shared[1]], ox, oy)];
}

/** Pixel anchor for a board-targeted action (vertex, edge, or hex). */
function actionAnchor(a: LegalAction, ox: number, oy: number): PixelCoord | null {
  if (a.value?.vertex) return centroid(a.value.vertex, ox, oy);
  if (a.value?.edge) {
    const [p1, p2] = edgeEndpoints(a.value.edge, ox, oy);
    return { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
  }
  if (a.value?.hex) return hexToPixel({ q: a.value.hex[0], r: a.value.hex[1] }, ox, oy);
  return null;
}

function drawCity(ctx: CanvasRenderingContext2D, c: PixelCoord, color: string) {
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.35)';
  ctx.shadowBlur = 4;
  ctx.fillStyle = color;
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 1.5;
  ctx.beginPath(); // wide base + tower with roof
  ctx.moveTo(c.x - 12, c.y + 8);
  ctx.lineTo(c.x - 12, c.y - 2);
  ctx.lineTo(c.x - 4, c.y - 2);
  ctx.lineTo(c.x - 4, c.y - 10);
  ctx.lineTo(c.x + 1, c.y - 15);
  ctx.lineTo(c.x + 6, c.y - 10);
  ctx.lineTo(c.x + 6, c.y - 2);
  ctx.lineTo(c.x + 12, c.y - 2);
  ctx.lineTo(c.x + 12, c.y + 8);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

export default function GameBoard({ game, mode, hint, disabled, onPick }: GameBoardProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<Target | null>(null);

  const targets: Target[] = [];
  const canvas = canvasRef.current;
  if (canvas && mode && !disabled) {
    const ox = canvas.width / 2;
    const oy = canvas.height / 2;
    for (const a of game.legal_actions) {
      if (a.type !== MODE_TYPES[mode]) continue;
      const p = actionAnchor(a, ox, oy);
      if (p) targets.push({ x: p.x, y: p.y, index: a.index });
    }
  }

  const nearest = (e: React.MouseEvent<HTMLCanvasElement>): Target | null => {
    const el = canvasRef.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let best: Target | null = null;
    let bestD = 20;
    for (const t of targets) {
      const d = Math.hypot(mx - t.x, my - t.y);
      if (d < bestD) { best = t; bestD = d; }
    }
    return best;
  };

  useEffect(() => {
    const el = canvasRef.current;
    const ctx = el?.getContext('2d');
    if (!el || !ctx) return;
    const rect = el.parentElement?.getBoundingClientRect();
    if (rect) { el.width = rect.width; el.height = rect.height; }
    const ox = el.width / 2;
    const oy = el.height / 2;

    // Ocean + island shore
    const ocean = ctx.createRadialGradient(ox, oy, 60, ox, oy, Math.max(el.width, el.height) * 0.7);
    ocean.addColorStop(0, '#1e5b8f');
    ocean.addColorStop(1, '#0c2742');
    ctx.fillStyle = ocean;
    ctx.fillRect(0, 0, el.width, el.height);
    const centers = game.hexes.map((h) => hexToPixel({ q: h.q, r: h.r }, ox, oy));
    centers.forEach((c) => fillHexShape(ctx, c, HEX_RADIUS * 1.62, 'rgba(120,190,230,0.18)'));
    centers.forEach((c) => fillHexShape(ctx, c, HEX_RADIUS * 1.3, '#e8d5a3'));
    centers.forEach((c) => fillHexShape(ctx, c, HEX_RADIUS * 1.22, '#d9c08a'));

    // Hexes: terrain, icon, number token, robber
    game.hexes.forEach((h, i) => {
      const c = centers[i];
      drawHex(ctx, c, getResourceColor(h.resource), 'rgba(15,23,42,0.45)', 2);
      ctx.font = '19px Arial';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(getResourceIcon(h.resource), c.x, c.y - 16);
      if (h.number !== null) drawNumberChip(ctx, { x: c.x, y: c.y + 13 }, h.number, 15);
      if (h.q === game.robber[0] && h.r === game.robber[1]) {
        ctx.fillStyle = 'rgba(30,41,59,0.92)';
        ctx.beginPath();
        ctx.arc(c.x - 22, c.y - 2, 11, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 12px Arial';
        ctx.fillText('R', c.x - 22, c.y - 1);
      }
    });

    // Ports: badge just outside each port vertex
    for (const port of game.ports) {
      const v = centroid(port.vertex, ox, oy);
      const bx = v.x + (v.x - ox) * 0.14;
      const by = v.y + (v.y - oy) * 0.14;
      const label = port.type === '3:1' ? '3:1' : `2:1${getResourceIcon(port.type)}`;
      ctx.font = 'bold 10px Arial';
      const w = ctx.measureText(label).width + 8;
      ctx.fillStyle = 'rgba(248,250,252,0.92)';
      ctx.beginPath();
      ctx.roundRect(bx - w / 2, by - 8, w, 16, 6);
      ctx.fill();
      ctx.fillStyle = '#0f172a';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(label, bx, by + 1);
    }

    // Roads along their true edges, then buildings on top
    for (const r of game.roads) {
      const [p1, p2] = edgeEndpoints(r.edge, ox, oy);
      drawRoad(ctx, p1, p2, PLAYER_COLORS[r.owner], 7);
    }
    for (const b of game.buildings) {
      const c = centroid(b.vertex, ox, oy);
      if (b.kind === 'city') drawCity(ctx, c, PLAYER_COLORS[b.owner]);
      else drawSettlement(ctx, c, PLAYER_COLORS[b.owner], 11);
    }

    // Legal placement targets for the active mode (glowing green)
    for (const t of targets) {
      ctx.fillStyle = 'rgba(134,239,172,0.22)';
      ctx.beginPath();
      ctx.arc(t.x, t.y, 13, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = 'rgba(187,247,208,0.9)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(t.x, t.y, 8, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Gold ring on the trainer's top recommendation (if board-targeted)
    if (hint) {
      const p = actionAnchor(hint, ox, oy);
      if (p) {
        ctx.strokeStyle = '#fbbf24';
        ctx.lineWidth = 3;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 17, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }

    // Hover preview
    if (hover) {
      ctx.strokeStyle = '#e2e8f0';
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(hover.x, hover.y, 12, 0, Math.PI * 2);
      ctx.stroke();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game, mode, hover, hint, disabled]);

  return (
    <canvas
      ref={canvasRef}
      className={`h-full w-full ${hover ? 'cursor-pointer' : 'cursor-default'}`}
      style={{ display: 'block' }}
      onMouseMove={(e) => setHover(nearest(e))}
      onMouseLeave={() => setHover(null)}
      onClick={(e) => {
        const t = nearest(e);
        if (t) { setHover(null); onPick(t.index); }
      }}
    />
  );
}
