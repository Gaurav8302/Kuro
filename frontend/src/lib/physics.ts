export interface Vec2 {
  x: number;
  y: number;
}

export function vec2(x: number, y: number): Vec2 {
  return { x, y };
}

export function add(a: Vec2, b: Vec2): Vec2 {
  return { x: a.x + b.x, y: a.y + b.y };
}

export function sub(a: Vec2, b: Vec2): Vec2 {
  return { x: a.x - b.x, y: a.y - b.y };
}

export function scale(v: Vec2, s: number): Vec2 {
  return { x: v.x * s, y: v.y * s };
}

export function len(v: Vec2): number {
  return Math.sqrt(v.x * v.x + v.y * v.y);
}

export function dist(a: Vec2, b: Vec2): number {
  return len(sub(a, b));
}

export function normalize(v: Vec2): Vec2 {
  const l = len(v);
  if (l < 1e-8) return { x: 0, y: 0 };
  return { x: v.x / l, y: v.y / l };
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function lerpVec2(a: Vec2, b: Vec2, t: number): Vec2 {
  return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) };
}

export function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

export function gaussianFalloff(distNorm: number, sigma: number): number {
  return Math.exp(-(distNorm * distNorm) / (2 * sigma * sigma));
}

export interface Blob {
  pos: Vec2;
  home: Vec2;
  vel: Vec2;
  baseRadius: number;
  radius: number;
  color: string;
  alpha: number;
  layer: number;
  depth: number;
  phase: number;
  noiseOffset: Vec2;
  driftFreq: Vec2;
  driftAmp: Vec2;
}
