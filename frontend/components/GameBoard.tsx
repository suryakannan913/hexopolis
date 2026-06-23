'use client';

import { useRef, useEffect, useState } from 'react';
import { useGameStore } from '@/store/gameStore';
import { buildSettlement, buildRoad } from '@/lib/api';
import {
  getStandardBoardHexes,
  hexToPixel,
  getHexVertices,
  getHexEdges,
  drawHex,
  drawHexBorder,
  getResourceColor,
  drawTextInHex,
  isPointInHex,
  getVertexPixelCoord,
  getEdgePixelCoord,
  drawSettlement,
  drawRoad,
  isPointNearVertex,
  isPointNearEdge,
  type HexCoord,
  type PixelCoord,
  type Vertex,
  type Edge,
} from '@/lib/hexUtils';

type BuildMode = 'none' | 'settlement' | 'road';

interface GameBoardProps {
  gameId: string;
  buildMode?: BuildMode;
  onBuildModeChange?: (mode: BuildMode) => void;
}

interface HexData {
  coord: HexCoord;
  resource: string | null;
  diceNumber: number | null;
}

export default function GameBoard({ gameId, buildMode = 'none', onBuildModeChange }: GameBoardProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gameState = useGameStore();
  const [hoveredHex, setHoveredHex] = useState<HexCoord | null>(null);
  const [hoveredVertex, setHoveredVertex] = useState<Vertex | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<Edge | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [boardHexes] = useState<HexData[]>(() => {
    const hexes = getStandardBoardHexes();
    const resources = ['wood', 'sheep', 'ore', 'brick', 'wheat', 'wood', 'wheat', 'ore', 'sheep', 'brick', 'wood', 'brick', 'wheat', 'sheep', 'ore', 'wood', 'wheat', 'sheep', 'brick'];
    const diceNumbers = [6, 5, 10, 8, 9, 4, 11, 3, 11, 4, 8, 10, 5, 6, 9, 2, 3, 12, 7];

    return hexes.map((hex, i) => ({
      coord: hex,
      resource: resources[i] || null,
      diceNumber: diceNumbers[i] || null,
    }));
  });

  // Get all vertices and edges
  const allVertices = boardHexes.flatMap((h) => getHexVertices(h.coord, boardHexes.map((x) => x.coord)));
  const allEdges = boardHexes.flatMap((h) => getHexEdges(h.coord));

  const handleCanvasClick = async (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (buildMode === 'none' || loading) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const pixelCoord: PixelCoord = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };

    const originX = canvas.width / 2;
    const originY = canvas.height / 2;

    setLoading(true);
    setError(null);

    try {
      if (buildMode === 'settlement' && hoveredVertex) {
        await buildSettlement(gameId, hoveredVertex.hexCoords.map((h) => [h.q, h.r]));
        gameState.setGameState({ lastDiceRoll: null });
      } else if (buildMode === 'road' && hoveredEdge) {
        await buildRoad(gameId, [hoveredEdge.hex1.q, hoveredEdge.hex1.r], [hoveredEdge.hex2.q, hoveredEdge.hex2.r]);
        gameState.setGameState({ lastDiceRoll: null });
      }
      onBuildModeChange?.('none');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to build');
    } finally {
      setLoading(false);
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const pixelCoord: PixelCoord = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };

    const originX = canvas.width / 2;
    const originY = canvas.height / 2;

    // Check hexes
    for (const hexData of boardHexes) {
      const pixelHex = hexToPixel(hexData.coord, originX, originY);
      if (isPointInHex(pixelCoord, pixelHex)) {
        setHoveredHex(hexData.coord);
        setHoveredVertex(null);
        setHoveredEdge(null);
        return;
      }
    }

    // Check vertices (settlements)
    if (buildMode === 'settlement') {
      for (const vertex of allVertices) {
        const pixelVertex = getVertexPixelCoord(vertex, originX, originY);
        if (isPointNearVertex(pixelCoord, pixelVertex)) {
          setHoveredVertex(vertex);
          setHoveredHex(null);
          setHoveredEdge(null);
          return;
        }
      }
    }

    // Check edges (roads)
    if (buildMode === 'road') {
      for (const edge of allEdges) {
        const p1 = hexToPixel(edge.hex1, originX, originY);
        const p2 = hexToPixel(edge.hex2, originX, originY);
        if (isPointNearEdge(pixelCoord, p1, p2)) {
          setHoveredEdge(edge);
          setHoveredHex(null);
          setHoveredVertex(null);
          return;
        }
      }
    }

    setHoveredHex(null);
    setHoveredVertex(null);
    setHoveredEdge(null);
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.parentElement?.getBoundingClientRect();
    if (rect) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    const originX = canvas.width / 2;
    const originY = canvas.height / 2;

    // Clear canvas
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw hexes
    boardHexes.forEach((hexData) => {
      const pixelCoord = hexToPixel(hexData.coord, originX, originY);
      const color = getResourceColor(hexData.resource);

      drawHex(ctx, pixelCoord, color, '#1e293b', 2);

      if (hoveredHex && hoveredHex.q === hexData.coord.q && hoveredHex.r === hexData.coord.r) {
        drawHexBorder(ctx, pixelCoord, '#60a5fa', 3);
      }

      if (hexData.diceNumber && hexData.diceNumber !== 7) {
        const textColor = ['wheat', 'wood'].includes(hexData.resource || '') ? '#000' : '#fff';
        drawTextInHex(ctx, hexData.diceNumber.toString(), pixelCoord, textColor, 18);
      }
    });

    // Draw settlements (placeholder - would come from backend)
    allVertices.forEach((vertex) => {
      const pixelVertex = getVertexPixelCoord(vertex, originX, originY);
      const isHovered = hoveredVertex &&
        JSON.stringify(hoveredVertex.hexCoords) === JSON.stringify(vertex.hexCoords);

      if (isHovered) {
        drawSettlement(ctx, pixelVertex, '#60a5fa', 12);
      }
    });

    // Draw roads (placeholder - would come from backend)
    allEdges.forEach((edge) => {
      const p1 = hexToPixel(edge.hex1, originX, originY);
      const p2 = hexToPixel(edge.hex2, originX, originY);
      const isHovered = hoveredEdge &&
        (JSON.stringify(hoveredEdge) === JSON.stringify(edge));

      if (isHovered) {
        drawRoad(ctx, p1, p2, '#60a5fa', 10);
      }
    });

    // Draw title
    ctx.fillStyle = '#e2e8f0';
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'left';
    ctx.fillText(`Turn: ${gameState.turnNumber} • ${gameState.currentPlayerName}`, 10, 20);

    if (buildMode !== 'none') {
      ctx.fillStyle = '#60a5fa';
      ctx.fillText(`Building: ${buildMode === 'settlement' ? '🏘️ Settlement' : '🛣️ Road'}`, 10, 40);
    }

    if (loading) {
      ctx.fillStyle = '#fbbf24';
      ctx.fillText('Building...', 10, 60);
    }

    if (error) {
      ctx.fillStyle = '#ef4444';
      ctx.fillText(`Error: ${error}`, 10, 60);
    }

    // Draw legend
    ctx.font = '12px Arial';
    ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'left';
    ctx.fillText('🌲 Wood  🌾 Wheat  ⛏️ Ore  🧱 Brick  🐑 Sheep', 10, canvas.height - 15);
  }, [boardHexes, hoveredHex, hoveredVertex, hoveredEdge, gameState.turnNumber, gameState.currentPlayerName, buildMode, loading, error, allVertices, allEdges]);

  return (
    <canvas
      ref={canvasRef}
      className={`w-full h-full bg-slate-950 ${buildMode !== 'none' ? 'cursor-crosshair' : 'cursor-pointer'}`}
      style={{ display: 'block' }}
      onClick={handleCanvasClick}
      onMouseMove={handleCanvasMouseMove}
      onMouseLeave={() => {
        setHoveredHex(null);
        setHoveredVertex(null);
        setHoveredEdge(null);
      }}
    />
  );
}
