'use client';

import { useRef, useEffect } from 'react';
import { useGameStore } from '@/store/gameStore';

interface GameBoardProps {
  gameId: string;
}

export default function GameBoard({ gameId: _gameId }: GameBoardProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gameState = useGameStore();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size to match container
    const rect = canvas.parentElement?.getBoundingClientRect();
    if (rect) {
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    // Clear canvas
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw placeholder board
    drawPlaceholderBoard(ctx, canvas.width, canvas.height);
  }, [gameState]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full bg-slate-800"
      style={{ display: 'block' }}
    />
  );
}

function drawPlaceholderBoard(ctx: CanvasRenderingContext2D, width: number, height: number) {
  // Draw title
  ctx.fillStyle = '#e2e8f0';
  ctx.font = 'bold 24px Arial';
  ctx.textAlign = 'center';
  ctx.fillText('Hexagonal Board (Coming Soon)', width / 2, 50);

  // Draw hex grid placeholder
  ctx.fillStyle = '#475569';
  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 2;

  const hexRadius = 40;
  const spacing = hexRadius * 2.3;
  const startX = 60;
  const startY = 120;

  for (let row = 0; row < 5; row++) {
    for (let col = 0; col < 6; col++) {
      const x = startX + col * spacing + (row % 2) * (spacing / 2);
      const y = startY + row * spacing * 0.75;

      if (x < width - 40 && y < height - 40) {
        drawHex(ctx, x, y, hexRadius);
      }
    }
  }

  // Draw legend
  ctx.fillStyle = '#cbd5e1';
  ctx.font = '14px Arial';
  ctx.textAlign = 'left';
  ctx.fillText('Resources: 🌲 Wood  🌾 Wheat  ⛏️ Ore  🧱 Brick  🐑 Sheep', 60, height - 60);
  ctx.fillText('Canvas rendering in development - Phase 2.2', 60, height - 30);
}

function drawHex(ctx: CanvasRenderingContext2D, centerX: number, centerY: number, radius: number) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (i * 60 - 90) * (Math.PI / 180);
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}
