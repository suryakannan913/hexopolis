/**
 * Hexagonal board utilities for Canvas rendering.
 * Uses axial coordinates (q, r) from backend and converts to pixel coordinates.
 */

export interface HexCoord {
  q: number;
  r: number;
}

export interface PixelCoord {
  x: number;
  y: number;
}

// Hex size - adjustable for zoom
const HEX_RADIUS = 50;
const HEX_WIDTH = HEX_RADIUS * 2;
const HEX_HEIGHT = (HEX_RADIUS * Math.sqrt(3)) / 2;

// Spacing between hex centers (for pointy-top hexagons)
const HEX_SPACING_X = HEX_WIDTH * 0.75;
const HEX_SPACING_Y = HEX_HEIGHT + HEX_RADIUS / 2;

/**
 * Convert axial hex coordinates to pixel coordinates.
 * Assumes pointy-top hexagons centered around origin.
 */
export function hexToPixel(hex: HexCoord, originX: number, originY: number): PixelCoord {
  const x = originX + HEX_SPACING_X * (hex.q + hex.r / 2);
  const y = originY + HEX_SPACING_Y * hex.r;
  return { x, y };
}

/**
 * Convert pixel coordinates to axial hex coordinates (inverse operation).
 */
export function pixelToHex(pixel: PixelCoord, originX: number, originY: number): HexCoord {
  const x = (pixel.x - originX) / HEX_SPACING_X;
  const y = (pixel.y - originY) / HEX_SPACING_Y;

  const q = x - y / 2;
  const r = y;

  // Round to nearest hex (cube rounding)
  return roundHex({ q, r });
}

/**
 * Round fractional hex coordinates to nearest integer hex.
 */
function roundHex(hex: HexCoord): HexCoord {
  let q = Math.round(hex.q);
  let r = Math.round(hex.r);
  const s = Math.round(-hex.q - hex.r);

  const q_diff = Math.abs(q - hex.q);
  const r_diff = Math.abs(r - hex.r);
  const s_diff = Math.abs(s - (-hex.q - hex.r));

  if (q_diff > r_diff && q_diff > s_diff) {
    q = -r - s;
  } else if (r_diff > s_diff) {
    r = -q - s;
  }

  return { q, r };
}

/**
 * Get the 6 vertices (corners) of a hex in pixel coordinates.
 */
export function getHexVertices(center: PixelCoord): PixelCoord[] {
  const vertices: PixelCoord[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i; // 60 degrees per vertex
    const x = center.x + HEX_RADIUS * Math.cos(angle);
    const y = center.y + HEX_RADIUS * Math.sin(angle);
    vertices.push({ x, y });
  }
  return vertices;
}

/**
 * Draw a hexagon on the canvas.
 */
export function drawHex(
  ctx: CanvasRenderingContext2D,
  center: PixelCoord,
  fillColor: string,
  strokeColor: string = '#333',
  lineWidth: number = 2
) {
  const vertices = getHexVertices(center);

  // Fill
  ctx.fillStyle = fillColor;
  ctx.beginPath();
  ctx.moveTo(vertices[0].x, vertices[0].y);
  for (let i = 1; i < vertices.length; i++) {
    ctx.lineTo(vertices[i].x, vertices[i].y);
  }
  ctx.closePath();
  ctx.fill();

  // Stroke
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = lineWidth;
  ctx.stroke();
}

/**
 * Draw a hexagon with just a border (no fill).
 */
export function drawHexBorder(
  ctx: CanvasRenderingContext2D,
  center: PixelCoord,
  strokeColor: string,
  lineWidth: number = 2
) {
  const vertices = getHexVertices(center);
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  ctx.moveTo(vertices[0].x, vertices[0].y);
  for (let i = 1; i < vertices.length; i++) {
    ctx.lineTo(vertices[i].x, vertices[i].y);
  }
  ctx.closePath();
  ctx.stroke();
}

/**
 * Get the resource color for a given resource type.
 */
export function getResourceColor(resource: string | null): string {
  const colors: Record<string, string> = {
    wood: '#2f6b4f', // forest
    wheat: '#e0a82e', // field
    ore: '#8a93a6', // mountain
    brick: '#b85335', // hills
    sheep: '#7cb98f', // pasture
  };
  return colors[resource || ''] || '#cdbd97'; // desert sand
}

const RESOURCE_ICON: Record<string, string> = {
  wood: '🌲',
  wheat: '🌾',
  ore: '⛏️',
  brick: '🧱',
  sheep: '🐑',
};

export function getResourceIcon(resource: string | null): string {
  return RESOURCE_ICON[resource || ''] || '🏜️';
}

/**
 * Check if a pixel point is inside a hex.
 */
export function isPointInHex(point: PixelCoord, hexCenter: PixelCoord): boolean {
  const dx = point.x - hexCenter.x;
  const dy = point.y - hexCenter.y;
  const distance = Math.sqrt(dx * dx + dy * dy);
  return distance <= HEX_RADIUS;
}

/**
 * Get all standard Catan board hexes in axial coordinates.
 */
export function getStandardBoardHexes(): HexCoord[] {
  return [
    // Center
    { q: 0, r: 0 },
    // Ring 1
    { q: 1, r: 0 },
    { q: 1, r: -1 },
    { q: 0, r: -1 },
    { q: -1, r: 0 },
    { q: -1, r: 1 },
    { q: 0, r: 1 },
    // Ring 2
    { q: 2, r: 0 },
    { q: 2, r: -1 },
    { q: 2, r: -2 },
    { q: 1, r: -2 },
    { q: 0, r: -2 },
    { q: -1, r: -1 },
    { q: -2, r: 0 },
    { q: -2, r: 1 },
    { q: -2, r: 2 },
    { q: -1, r: 2 },
    { q: 0, r: 2 },
    { q: 1, r: 1 },
  ];
}

/**
 * Draw text centered in a hex.
 */
export function drawTextInHex(
  ctx: CanvasRenderingContext2D,
  text: string,
  center: PixelCoord,
  color: string = '#000',
  fontSize: number = 16
) {
  ctx.fillStyle = color;
  ctx.font = `bold ${fontSize}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, center.x, center.y);
}

/**
 * Represents a vertex (settlement location) as 3 adjacent hex coordinates.
 */
export interface Vertex {
  hexCoords: [HexCoord, HexCoord, HexCoord];
}

/**
 * Represents an edge (road location) as 2 adjacent hex coordinates.
 */
export interface Edge {
  hex1: HexCoord;
  hex2: HexCoord;
}

/**
 * Get all 6 settlement vertices of a hex.
 * Each vertex is shared by up to 3 hexes.
 */
export function getSettlementVertices(hexCoord: HexCoord, _allHexes: HexCoord[]): Vertex[] {
  const neighbors = getHexNeighbors(hexCoord);
  const vertices: Vertex[] = [];

  for (let i = 0; i < 6; i++) {
    const neighbor1 = neighbors[i];
    const neighbor2 = neighbors[(i + 1) % 6];

    // Create vertex from the hex and its two adjacent neighbors
    const hexes = [hexCoord, neighbor1, neighbor2].sort((a, b) => {
      if (a.q !== b.q) return a.q - b.q;
      return a.r - b.r;
    });

    vertices.push({
      hexCoords: [hexes[0], hexes[1], hexes[2]],
    });
  }

  return vertices;
}

/**
 * Get the 6 neighbors of a hex in axial coordinates.
 */
function getHexNeighbors(hex: HexCoord): HexCoord[] {
  const directions = [
    { q: 1, r: 0 },
    { q: 1, r: -1 },
    { q: 0, r: -1 },
    { q: -1, r: 0 },
    { q: -1, r: 1 },
    { q: 0, r: 1 },
  ];

  return directions.map((dir) => ({
    q: hex.q + dir.q,
    r: hex.r + dir.r,
  }));
}

/**
 * Get the pixel coordinates of a vertex (settlement location).
 */
export function getVertexPixelCoord(
  vertex: Vertex,
  originX: number,
  originY: number
): PixelCoord {
  // Average the pixel coordinates of the 3 hexes
  const pixelCoords = vertex.hexCoords.map((hex) => hexToPixel(hex, originX, originY));
  return {
    x: (pixelCoords[0].x + pixelCoords[1].x + pixelCoords[2].x) / 3,
    y: (pixelCoords[0].y + pixelCoords[1].y + pixelCoords[2].y) / 3,
  };
}

/**
 * Get all edges (roads) connected to a hex.
 */
export function getHexEdges(hexCoord: HexCoord): Edge[] {
  const neighbors = getHexNeighbors(hexCoord);
  const edges: Edge[] = [];

  for (const neighbor of neighbors) {
    edges.push({
      hex1: hexCoord,
      hex2: neighbor,
    });
  }

  return edges;
}

/**
 * Get pixel coordinates for an edge (midpoint between two hex centers).
 */
export function getEdgePixelCoord(
  edge: Edge,
  originX: number,
  originY: number
): PixelCoord {
  const p1 = hexToPixel(edge.hex1, originX, originY);
  const p2 = hexToPixel(edge.hex2, originX, originY);
  return {
    x: (p1.x + p2.x) / 2,
    y: (p1.y + p2.y) / 2,
  };
}

/**
 * Draw a settlement as a little house (square base + triangular roof).
 */
export function drawSettlement(
  ctx: CanvasRenderingContext2D,
  center: PixelCoord,
  color: string,
  size: number = 10
) {
  const s = size;
  const x = center.x;
  const y = center.y;

  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.35)';
  ctx.shadowBlur = 4;
  ctx.shadowOffsetY = 1;

  ctx.fillStyle = color;
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 1.5;
  ctx.lineJoin = 'round';

  ctx.beginPath();
  // roof peak
  ctx.moveTo(x, y - s);
  ctx.lineTo(x + s * 0.85, y - s * 0.25);
  ctx.lineTo(x + s * 0.6, y - s * 0.25);
  // right wall
  ctx.lineTo(x + s * 0.6, y + s * 0.7);
  // base
  ctx.lineTo(x - s * 0.6, y + s * 0.7);
  // left wall
  ctx.lineTo(x - s * 0.6, y - s * 0.25);
  ctx.lineTo(x - s * 0.85, y - s * 0.25);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

/**
 * Draw a placement marker (hollow ring) for an empty buildable vertex.
 */
export function drawVertexMarker(
  ctx: CanvasRenderingContext2D,
  center: PixelCoord,
  color: string = 'rgba(226, 232, 240, 0.5)',
  radius: number = 4
) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
  ctx.fill();
}

/**
 * Draw a road as a thick rounded segment with a dark outline.
 */
export function drawRoad(
  ctx: CanvasRenderingContext2D,
  p1: PixelCoord,
  p2: PixelCoord,
  color: string,
  width: number = 7
) {
  ctx.lineCap = 'round';

  // dark outline
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = width + 3;
  ctx.beginPath();
  ctx.moveTo(p1.x, p1.y);
  ctx.lineTo(p2.x, p2.y);
  ctx.stroke();

  // colored core
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(p1.x, p1.y);
  ctx.lineTo(p2.x, p2.y);
  ctx.stroke();
}

/**
 * Number of ways two dice produce a roll (its frequency out of 36).
 */
export function rollFrequency(n: number): number {
  return 6 - Math.abs(7 - n);
}

/**
 * Draw a Catan-style number token: a cream disc with the roll number and
 * probability pips. 6 and 8 (the most likely) are emphasized in red.
 */
export function drawNumberChip(
  ctx: CanvasRenderingContext2D,
  center: PixelCoord,
  num: number,
  radius: number = 16
) {
  const x = center.x;
  const y = center.y;
  const hot = num === 6 || num === 8;

  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.3)';
  ctx.shadowBlur = 4;
  ctx.shadowOffsetY = 1;
  ctx.fillStyle = '#f5ecd7';
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();

  ctx.strokeStyle = hot ? '#b91c1c' : '#9ca3af';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.stroke();

  // number
  ctx.fillStyle = hot ? '#b91c1c' : '#1f2937';
  ctx.font = `bold ${Math.round(radius * 1.05)}px Georgia, serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(String(num), x, y - radius * 0.12);

  // probability pips
  const pips = rollFrequency(num);
  const pipR = 1.3;
  const gap = 3.4;
  const startX = x - ((pips - 1) * gap) / 2;
  const pipY = y + radius * 0.62;
  ctx.fillStyle = hot ? '#b91c1c' : '#4b5563';
  for (let i = 0; i < pips; i++) {
    ctx.beginPath();
    ctx.arc(startX + i * gap, pipY, pipR, 0, Math.PI * 2);
    ctx.fill();
  }
}

/**
 * Check if a point is close to a vertex.
 */
export function isPointNearVertex(point: PixelCoord, vertex: PixelCoord, radius: number = 12): boolean {
  const dx = point.x - vertex.x;
  const dy = point.y - vertex.y;
  const distance = Math.sqrt(dx * dx + dy * dy);
  return distance <= radius;
}

/**
 * Check if a point is close to a line segment (edge).
 */
export function isPointNearEdge(
  point: PixelCoord,
  p1: PixelCoord,
  p2: PixelCoord,
  distance: number = 8
): boolean {
  // Vector from p1 to p2
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const lenSq = dx * dx + dy * dy;

  if (lenSq === 0) return isPointNearVertex(point, p1, distance);

  // Parameter t of closest point on line segment
  const t = Math.max(0, Math.min(1, ((point.x - p1.x) * dx + (point.y - p1.y) * dy) / lenSq));

  const closestX = p1.x + t * dx;
  const closestY = p1.y + t * dy;

  const pdx = point.x - closestX;
  const pdy = point.y - closestY;
  return Math.sqrt(pdx * pdx + pdy * pdy) <= distance;
}
