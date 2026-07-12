/**
 * Hex geometry for the SVG board. Pointy-top hexagons in axial coordinates,
 * centered on the SVG origin — the viewBox does all scaling, so there is no
 * pixel math against a canvas size anywhere.
 */
export const HEX_RADIUS = 52;
const SQRT3 = Math.sqrt(3);
const SPACING_X = SQRT3 * HEX_RADIUS;
const SPACING_Y = 1.5 * HEX_RADIUS;

export interface HexCoord { q: number; r: number }
export interface PixelCoord { x: number; y: number }

export function hexToPixel(hex: HexCoord, ox = 0, oy = 0): PixelCoord {
  return {
    x: ox + SPACING_X * (hex.q + hex.r / 2),
    y: oy + SPACING_Y * hex.r,
  };
}

/** The 6 corners of a pointy-top hex. */
export function hexCorners(center: PixelCoord, radius: number = HEX_RADIUS): PixelCoord[] {
  const pts: PixelCoord[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    pts.push({ x: center.x + radius * Math.cos(angle), y: center.y + radius * Math.sin(angle) });
  }
  return pts;
}

/** SVG points attribute for a polygon. */
export function pointsAttr(pts: PixelCoord[]): string {
  return pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
}
