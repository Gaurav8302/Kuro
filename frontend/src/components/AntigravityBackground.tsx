import React, { useEffect, useRef, useMemo } from 'react';
import { useOptimizedAnimations } from '../hooks/use-performance';

// ─────────────────────────────────────────────────────────────────────
//  AntigravityBackground – Physics-based, field-distorted, multi-layer
//  interactive background with organic idle motion & premium rendering.
// ─────────────────────────────────────────────────────────────────────

// ─── Configuration ───────────────────────────────────────────────────
interface AntigravityConfig {
  /** Total dash count (across all layers) */
  dashCount: number;
  /** Number of depth layers */
  layerCount: number;
  /** Radius of cursor force field (px) */
  fieldRadius: number;
  /** Peak repulsion strength */
  fieldStrength: number;
  /** Gaussian sigma for falloff (fraction of fieldRadius) */
  fieldSigma: number;
  /** How quickly cursor velocity boosts the field */
  cursorVelocityBoost: number;
  /** Damping / friction per frame (0.95 = heavy, 0.99 = icy) */
  damping: number;
  /** Spring constant pulling dashes back to home */
  springK: number;
  /** Perlin noise scroll speed */
  noiseSpeed: number;
  /** Perlin noise amplitude (px) */
  noiseAmplitude: number;
  /** Perlin noise spatial scale */
  noiseScale: number;
  /** Lerp factor for smoothing cursor position */
  cursorLerp: number;
  /** Global glow intensity (0-1) */
  glowIntensity: number;
}

const DEFAULT_CONFIG: AntigravityConfig = {
  dashCount: 1400,
  layerCount: 4,
  fieldRadius: 240,
  fieldStrength: 18,
  fieldSigma: 0.38,
  cursorVelocityBoost: 0.6,
  damping: 0.94,
  springK: 0.004,
  noiseSpeed: 0.00025,
  noiseAmplitude: 30,
  noiseScale: 0.0018,
  cursorLerp: 0.08,
  glowIntensity: 0.7,
};

// ─── Color palette (Google-inspired spectrum) ────────────────────────
const LAYER_PALETTES: string[][] = [
  // Layer 0 (farthest back) – muted blues / grays
  ['#8ab4f8', '#aecbfa', '#b0c4de', '#94a3b8', '#7dd3fc'],
  // Layer 1 – soft purples & teals
  ['#a78bfa', '#7c3aed', '#06b6d4', '#67e8f9', '#818cf8'],
  // Layer 2 – warm reds / oranges / yellows
  ['#f87171', '#fb923c', '#fbbf24', '#f97316', '#fb7185'],
  // Layer 3 (foreground) – vivid primaries
  ['#4285f4', '#ea4335', '#34a853', '#fbbc04', '#ff6d5a'],
];

// ─── Perlin noise (improved) ─────────────────────────────────────────
class PerlinNoise {
  private readonly perm: Uint8Array;

  constructor(seed = 42) {
    const p = new Uint8Array(256);
    for (let i = 0; i < 256; i++) p[i] = i;
    let s = seed;
    for (let i = 255; i > 0; i--) {
      s = (s * 16807) % 2147483647;
      const j = s % (i + 1);
      [p[i], p[j]] = [p[j], p[i]];
    }
    this.perm = new Uint8Array(512);
    for (let i = 0; i < 512; i++) this.perm[i] = p[i & 255];
  }

  private fade(t: number) { return t * t * t * (t * (t * 6 - 15) + 10); }

  private grad(hash: number, x: number, y: number): number {
    const h = hash & 3;
    const u = h < 2 ? x : y;
    const v = h < 2 ? y : x;
    return ((h & 1) ? -u : u) + ((h & 2) ? -v : v);
  }

  noise2D(x: number, y: number): number {
    const X = Math.floor(x) & 255;
    const Y = Math.floor(y) & 255;
    const xf = x - Math.floor(x);
    const yf = y - Math.floor(y);
    const u = this.fade(xf);
    const v = this.fade(yf);
    const aa = this.perm[this.perm[X] + Y];
    const ab = this.perm[this.perm[X] + Y + 1];
    const ba = this.perm[this.perm[X + 1] + Y];
    const bb = this.perm[this.perm[X + 1] + Y + 1];
    const lx1 = this.grad(aa, xf, yf) + u * (this.grad(ba, xf - 1, yf) - this.grad(aa, xf, yf));
    const lx2 = this.grad(ab, xf, yf - 1) + u * (this.grad(bb, xf - 1, yf - 1) - this.grad(ab, xf, yf - 1));
    return lx1 + v * (lx2 - lx1);
  }

  /** Fractal Brownian Motion – layered noise for richer motion */
  fbm(x: number, y: number, octaves = 3): number {
    let val = 0, amp = 1, freq = 1, max = 0;
    for (let i = 0; i < octaves; i++) {
      val += this.noise2D(x * freq, y * freq) * amp;
      max += amp;
      amp *= 0.5;
      freq *= 2;
    }
    return val / max;
  }
}

// ─── Dash element ────────────────────────────────────────────────────
interface Dash {
  // Position
  x: number;
  y: number;
  // Home position (rest)
  homeX: number;
  homeY: number;
  // Velocity
  vx: number;
  vy: number;
  // Rendering
  length: number;
  thickness: number;
  angle: number;        // current visual angle
  baseAngle: number;    // resting angle (from noise)
  color: string;
  maxOpacity: number;
  // Depth
  layer: number;
  /** 0..1 – 0 is far, 1 is near */
  depth: number;
  /** Per-dash noise phase offset */
  noisePhaseX: number;
  noisePhaseY: number;
  /** Sinusoidal drift parameters */
  driftFreqX: number;
  driftFreqY: number;
  driftAmpX: number;
  driftAmpY: number;
  driftPhaseX: number;
  driftPhaseY: number;
}

// ─── Smoothed cursor state (internal to animation loop) ──────────────
interface CursorState {
  rawX: number;
  rawY: number;
  /** Smoothed / lerped position */
  x: number;
  y: number;
  /** Smoothed velocity */
  velX: number;
  velY: number;
  prevX: number;
  prevY: number;
  active: boolean;
  /** Speed magnitude (smoothed) */
  speed: number;
}

// ─── Helper ──────────────────────────────────────────────────────────
function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }

function gaussianFalloff(distNorm: number, sigma: number): number {
  // distNorm in [0,1], returns [0,1]
  return Math.exp(-(distNorm * distNorm) / (2 * sigma * sigma));
}

// ─── Component ───────────────────────────────────────────────────────
interface AntigravityBackgroundProps {
  config?: Partial<AntigravityConfig>;
  className?: string;
  style?: React.CSSProperties;
}

const AntigravityBackground: React.FC<AntigravityBackgroundProps> = ({
  config: userConfig,
  className = '',
  style,
}) => {
  const { shouldReduceAnimations, particleCount } = useOptimizedAnimations();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const dashesRef = useRef<Dash[]>([]);
  const noiseRef = useRef(new PerlinNoise(42));
  const timeRef = useRef(0);
  const sizeRef = useRef({ w: 0, h: 0 });
  const cursorRef = useRef<CursorState>({
    rawX: -9999, rawY: -9999,
    x: -9999, y: -9999,
    velX: 0, velY: 0,
    prevX: -9999, prevY: -9999,
    active: false,
    speed: 0,
  });

  const config = useMemo<AntigravityConfig>(
    () => ({ ...DEFAULT_CONFIG, ...userConfig }),
    [userConfig],
  );
  const cfgRef = useRef(config);
  useEffect(() => { cfgRef.current = config; }, [config]);

  // ─── Initialize dashes ──────────────────────────────────────────
  const initDashes = (w: number, h: number) => {
    const cfg = cfgRef.current;
    const noise = noiseRef.current;
    const dashes: Dash[] = [];
    const perLayer = Math.floor(cfg.dashCount / cfg.layerCount);

    for (let layer = 0; layer < cfg.layerCount; layer++) {
      const count = layer === cfg.layerCount - 1
        ? cfg.dashCount - perLayer * (cfg.layerCount - 1)
        : perLayer;

      const depth = layer / Math.max(cfg.layerCount - 1, 1); // 0..1
      const palette = LAYER_PALETTES[Math.min(layer, LAYER_PALETTES.length - 1)];

      for (let i = 0; i < count; i++) {
        // Distribute with gaussian-ish clustering toward center for far layers,
        // more uniform for near layers
        let x: number, y: number;
        if (Math.random() < (0.6 - depth * 0.3)) {
          // Clustered
          const u1 = Math.random(), u2 = Math.random();
          const r = Math.sqrt(-2 * Math.log(Math.max(u1, 1e-5)));
          const theta = Math.PI * 2 * u2;
          x = w / 2 + r * Math.cos(theta) * w * 0.22;
          y = h / 2 + r * Math.sin(theta) * h * 0.22;
        } else {
          x = Math.random() * w;
          y = Math.random() * h;
        }
        x = Math.max(-60, Math.min(w + 60, x));
        y = Math.max(-60, Math.min(h + 60, y));

        // Size scales with depth
        const sizeMul = 0.3 + depth * 0.7;
        const length = (2 + Math.random() * 10) * sizeMul;
        const thickness = (0.5 + Math.random() * 1.8) * sizeMul;

        // Base angle from noise field
        const nVal = noise.noise2D(x * 0.003, y * 0.003);
        const baseAngle = nVal * Math.PI * 2;

        // Opacity: far layers are dimmer
        const maxOpacity = (0.15 + depth * 0.55) * (0.5 + Math.random() * 0.5);

        const color = palette[Math.floor(Math.random() * palette.length)];

        dashes.push({
          x, y,
          homeX: x, homeY: y,
          vx: 0, vy: 0,
          length, thickness,
          angle: baseAngle,
          baseAngle,
          color,
          maxOpacity,
          layer,
          depth,
          noisePhaseX: Math.random() * 1000,
          noisePhaseY: Math.random() * 1000,
          driftFreqX: 0.0003 + Math.random() * 0.0006,
          driftFreqY: 0.0003 + Math.random() * 0.0006,
          driftAmpX: (3 + Math.random() * 8) * (0.3 + depth * 0.7),
          driftAmpY: (3 + Math.random() * 8) * (0.3 + depth * 0.7),
          driftPhaseX: Math.random() * Math.PI * 2,
          driftPhaseY: Math.random() * Math.PI * 2,
        });
      }
    }
    // Sort back-to-front
    dashes.sort((a, b) => a.layer - b.layer);
    dashesRef.current = dashes;
  };

  // ─── Main effect (animation loop) ──────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    // ── Resize handler ──
    const handleResize = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width, h = rect.height;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      sizeRef.current = { w, h };
      initDashes(w, h);
    };
    handleResize();

    // ── Mouse / touch handlers ──
    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      cursorRef.current.rawX = e.clientX - rect.left;
      cursorRef.current.rawY = e.clientY - rect.top;
      cursorRef.current.active = true;
    };
    const onMouseLeave = () => { cursorRef.current.active = false; };
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length) {
        const rect = canvas.getBoundingClientRect();
        cursorRef.current.rawX = e.touches[0].clientX - rect.left;
        cursorRef.current.rawY = e.touches[0].clientY - rect.top;
        cursorRef.current.active = true;
      }
    };
    const onTouchEnd = () => { cursorRef.current.active = false; };

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseleave', onMouseLeave);
    window.addEventListener('touchmove', onTouchMove, { passive: true });
    window.addEventListener('touchend', onTouchEnd);
    window.addEventListener('resize', handleResize);

    const noise = noiseRef.current;

    // ── Animation loop ──────────────────────────────────────────
    const animate = () => {
      const cfg = cfgRef.current;
      const cur = cursorRef.current;
      const { w, h } = sizeRef.current;
      const time = timeRef.current++;

      // Clear
      ctx.clearRect(0, 0, w, h);

      // ── Smooth cursor with heavy inertia ──
      if (cur.active) {
        cur.x = lerp(cur.x, cur.rawX, cfg.cursorLerp);
        cur.y = lerp(cur.y, cur.rawY, cfg.cursorLerp);
      } else {
        // Slowly drift cursor influence off-screen
        cur.x = lerp(cur.x, -9999, 0.01);
        cur.y = lerp(cur.y, -9999, 0.01);
      }

      // Smoothed cursor velocity
      const rawVelX = cur.x - cur.prevX;
      const rawVelY = cur.y - cur.prevY;
      cur.velX = lerp(cur.velX, rawVelX, 0.15);
      cur.velY = lerp(cur.velY, rawVelY, 0.15);
      cur.speed = lerp(cur.speed, Math.sqrt(cur.velX * cur.velX + cur.velY * cur.velY), 0.12);
      cur.prevX = cur.x;
      cur.prevY = cur.y;

      const fieldRadSq = cfg.fieldRadius * cfg.fieldRadius;
      const noiseTime = time * cfg.noiseSpeed;

      const dashes = dashesRef.current;
      const len = dashes.length;

      for (let i = 0; i < len; i++) {
        const d = dashes[i];

        // ────────────────────────────────────────────────────────
        //  1. ORGANIC IDLE MOTION (Perlin noise + sinusoidal drift)
        // ────────────────────────────────────────────────────────
        const nxCoord = (d.homeX + d.noisePhaseX) * cfg.noiseScale + noiseTime * 1.7;
        const nyCoord = (d.homeY + d.noisePhaseY) * cfg.noiseScale + noiseTime * 1.3;
        const noiseOffX = noise.fbm(nxCoord, nyCoord, 3) * cfg.noiseAmplitude * d.depth;
        const noiseOffY = noise.fbm(nxCoord + 100, nyCoord + 100, 3) * cfg.noiseAmplitude * d.depth;

        // Sinusoidal low-frequency drift (breathing)
        const sinOffX = Math.sin(time * d.driftFreqX + d.driftPhaseX) * d.driftAmpX;
        const sinOffY = Math.cos(time * d.driftFreqY + d.driftPhaseY) * d.driftAmpY;

        // Combined idle target = home + noise + drift
        const idleX = d.homeX + noiseOffX + sinOffX;
        const idleY = d.homeY + noiseOffY + sinOffY;

        // ────────────────────────────────────────────────────────
        //  2. CURSOR FORCE FIELD (Gaussian falloff repulsion)
        // ────────────────────────────────────────────────────────
        const dxCur = d.x - cur.x;
        const dyCur = d.y - cur.y;
        const distSq = dxCur * dxCur + dyCur * dyCur;

        // Depth-scaled field radius: foreground reacts more
        const effectiveRadius = cfg.fieldRadius * (0.5 + d.depth * 0.7);
        const effectiveRadSq = effectiveRadius * effectiveRadius;

        let fieldFx = 0, fieldFy = 0;

        if (distSq < effectiveRadSq * 4 && distSq > 0.1) {
          const dist = Math.sqrt(distSq);
          const distNorm = dist / effectiveRadius;

          // Gaussian falloff
          const influence = gaussianFalloff(distNorm, cfg.fieldSigma);

          // Boost by cursor speed
          const speedBoost = 1 + cur.speed * cfg.cursorVelocityBoost;

          // Force magnitude
          const forceMag = cfg.fieldStrength * influence * d.depth * speedBoost;

          // Direction: repel away from cursor
          const nx = dxCur / dist;
          const ny = dyCur / dist;

          fieldFx = nx * forceMag;
          fieldFy = ny * forceMag;

          // Add a tangential swirl component for richer motion
          const swirlFactor = influence * cfg.fieldStrength * 0.15 * d.depth;
          fieldFx += -ny * swirlFactor;
          fieldFy += nx * swirlFactor;
        }

        // ────────────────────────────────────────────────────────
        //  3. SPRING RESTORATION (to idle target, not just home)
        // ────────────────────────────────────────────────────────
        const toIdleX = idleX - d.x;
        const toIdleY = idleY - d.y;
        // Spring is softer for deeper layers (more lazy restoration)
        const springMul = cfg.springK * (0.3 + d.depth * 0.7);
        const springFx = toIdleX * springMul;
        const springFy = toIdleY * springMul;

        // ────────────────────────────────────────────────────────
        //  4. PHYSICS INTEGRATION
        // ────────────────────────────────────────────────────────
        // Acceleration
        d.vx += fieldFx + springFx;
        d.vy += fieldFy + springFy;

        // Damping (heavier for far layers = viscous)
        const layerDamping = cfg.damping - (1 - d.depth) * 0.03;
        d.vx *= layerDamping;
        d.vy *= layerDamping;

        // Integrate position
        d.x += d.vx;
        d.y += d.vy;

        // ────────────────────────────────────────────────────────
        //  5. ANGLE – smoothly orient along velocity or noise field
        // ────────────────────────────────────────────────────────
        const speed = Math.sqrt(d.vx * d.vx + d.vy * d.vy);
        let targetAngle: number;
        if (speed > 0.3) {
          // Align with velocity when moving
          targetAngle = Math.atan2(d.vy, d.vx);
        } else {
          // Rest: use noise-driven base angle that slowly evolves
          const noiseAngle = noise.noise2D(
            d.homeX * 0.002 + noiseTime * 0.5,
            d.homeY * 0.002 + noiseTime * 0.5,
          ) * Math.PI * 2;
          targetAngle = noiseAngle;
          d.baseAngle = noiseAngle; // update base for consistency
        }

        // Shortest-arc lerp for angle
        let angleDiff = targetAngle - d.angle;
        if (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
        if (angleDiff < -Math.PI) angleDiff += Math.PI * 2;
        const angleLerpSpeed = speed > 0.3 ? 0.06 : 0.015;
        d.angle += angleDiff * angleLerpSpeed;

        // ────────────────────────────────────────────────────────
        //  6. RENDERING – soft capsules with glow
        // ────────────────────────────────────────────────────────
        const halfLen = d.length * 0.5;
        const cosA = Math.cos(d.angle);
        const sinA = Math.sin(d.angle);
        const x1 = d.x - cosA * halfLen;
        const y1 = d.y - sinA * halfLen;
        const x2 = d.x + cosA * halfLen;
        const y2 = d.y + sinA * halfLen;

        // Skip if off screen
        if (d.x < -80 || d.x > w + 80 || d.y < -80 || d.y > h + 80) continue;

        // Opacity: base + slight boost when cursor is near
        let dynamicOpacity = d.maxOpacity;
        if (distSq < effectiveRadSq) {
          const distNorm = Math.sqrt(distSq) / effectiveRadius;
          const proximityBoost = gaussianFalloff(distNorm, 0.6) * 0.3;
          dynamicOpacity = Math.min(1, d.maxOpacity + proximityBoost);
        }

        ctx.globalAlpha = dynamicOpacity;
        ctx.lineCap = 'round';
        ctx.lineWidth = d.thickness;

        // Glow pass (soft shadow blur for foreground layers)
        if (d.layer >= cfgRef.current.layerCount - 2 && cfg.glowIntensity > 0) {
          ctx.save();
          ctx.shadowColor = d.color;
          ctx.shadowBlur = (4 + d.depth * 8) * cfg.glowIntensity;
          ctx.strokeStyle = d.color;
          ctx.globalAlpha = dynamicOpacity * 0.5;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
          ctx.restore();
        }

        // Main pass
        ctx.strokeStyle = d.color;
        ctx.globalAlpha = dynamicOpacity;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      ctx.globalAlpha = 1;
      ctx.shadowBlur = 0;
      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseleave', onMouseLeave);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('touchend', onTouchEnd);
      window.removeEventListener('resize', handleResize);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (shouldReduceAnimations) {
    return (
      <div
        className={`fixed inset-0 w-full h-full pointer-events-none ${className}`}
        style={{ zIndex: 1, background: 'radial-gradient(ellipse at 30% 50%, rgba(88,130,248,0.08) 0%, transparent 60%), radial-gradient(ellipse at 70% 20%, rgba(139,92,246,0.06) 0%, transparent 50%)', ...style }}
        aria-hidden="true"
      />
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className={`fixed inset-0 w-full h-full pointer-events-none ${className}`}
      style={{ zIndex: 1, ...style }}
      aria-hidden="true"
    />
  );
};

export default AntigravityBackground;
