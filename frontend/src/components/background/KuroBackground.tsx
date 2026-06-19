import React, { useRef, useEffect, useMemo, useCallback } from 'react';
import { useOptimizedAnimations } from '@/hooks/use-performance';
import { useMouseField, MouseField } from '@/hooks/useMouseField';
import { useAnimationEngine } from '@/hooks/useAnimationEngine';
import { PerlinNoise } from '@/lib/noise';
import { Blob, vec2, gaussianFalloff, clamp } from '@/lib/physics';

// ─── Configuration ───────────────────────────────────────────────────
interface KuroBackgroundConfig {
  blobCount: number;
  layerCount: number;
  fieldRadius: number;
  fieldStrength: number;
  fieldSigma: number;
  velocityBoost: number;
  damping: number;
  springK: number;
  noiseSpeed: number;
  noiseAmplitude: number;
  noiseScale: number;
  cursorLerp: number;
  maxRadius: number;
  minRadius: number;
  glowIntensity: number;
}

const DEFAULT_CONFIG: KuroBackgroundConfig = {
  blobCount: 120,
  layerCount: 4,
  fieldRadius: 300,
  fieldStrength: 14,
  fieldSigma: 0.4,
  velocityBoost: 0.8,
  damping: 0.93,
  springK: 0.003,
  noiseSpeed: 0.0003,
  noiseAmplitude: 35,
  noiseScale: 0.0015,
  cursorLerp: 0.06,
  maxRadius: 120,
  minRadius: 30,
  glowIntensity: 0.6,
};

// ─── Color palettes per layer ────────────────────────────────────────
const LAYER_COLORS: string[][] = [
  ['#7dd3fc', '#93c5fd', '#a5b4fc'],
  ['#818cf8', '#6ee7b7', '#67e8f9'],
  ['#c084fc', '#e879f9', '#f472b6'],
  ['#60a5fa', '#a78bfa', '#34d399'],
];

// ─── Component ───────────────────────────────────────────────────────
interface KuroBackgroundProps {
  config?: Partial<KuroBackgroundConfig>;
  className?: string;
  style?: React.CSSProperties;
}

const KuroBackground: React.FC<KuroBackgroundProps> = ({
  config: userConfig,
  className = '',
  style,
}) => {
  const { shouldReduceAnimations } = useOptimizedAnimations();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const blobsRef = useRef<Blob[]>([]);
  const noiseRef = useRef(new PerlinNoise(42));
  const sizeRef = useRef({ w: 0, h: 0 });
  const timeRef = useRef(0);
  const alphaRef = useRef(0);

  const cfg = useMemo<KuroBackgroundConfig>(
    () => ({ ...DEFAULT_CONFIG, ...userConfig }),
    [userConfig]
  );
  const cfgRef = useRef(cfg);
  useEffect(() => { cfgRef.current = cfg; }, [cfg]);

  const { fieldRef, update: updateMouse } = useMouseField({
    lerpFactor: cfg.cursorLerp,
  });

  // ─── Initialize blobs ──────────────────────────────────────────
  const initBlobs = useCallback((w: number, h: number) => {
    const c = cfgRef.current;
    const noise = noiseRef.current;
    const blobs: Blob[] = [];
    const perLayer = Math.floor(c.blobCount / c.layerCount);
    const activeLayerCount = shouldReduceAnimations
      ? Math.min(c.layerCount, 2)
      : c.layerCount;

    for (let layer = 0; layer < activeLayerCount; layer++) {
      const count = layer === activeLayerCount - 1
        ? c.blobCount - perLayer * (activeLayerCount - 1)
        : perLayer;
      const depth = layer / Math.max(activeLayerCount - 1, 1);
      const palette = LAYER_COLORS[Math.min(layer, LAYER_COLORS.length - 1)];

      for (let i = 0; i < count; i++) {
        let x: number, y: number;
        if (Math.random() < (0.5 - depth * 0.2)) {
          const u1 = Math.random(), u2 = Math.random();
          const r = Math.sqrt(-2 * Math.log(Math.max(u1, 1e-5)));
          const theta = Math.PI * 2 * u2;
          x = w * 0.5 + r * Math.cos(theta) * w * 0.2;
          y = h * 0.5 + r * Math.sin(theta) * h * 0.2;
        } else {
          x = Math.random() * w;
          y = Math.random() * h;
        }
        x = clamp(x, -w * 0.2, w * 1.2);
        y = clamp(y, -h * 0.2, h * 1.2);

        const sizeMul = 0.3 + depth * 0.7;
        const baseRadius = (c.minRadius + Math.random() * (c.maxRadius - c.minRadius)) * sizeMul;

        const nVal = noise.noise2D(x * c.noiseScale * 0.5, y * c.noiseScale * 0.5);
        const color = palette[Math.floor(Math.abs(nVal) * palette.length) % palette.length];
        const alpha = (0.08 + depth * 0.2) * (0.5 + Math.random() * 0.5);

        blobs.push({
          pos: vec2(x, y),
          home: vec2(x, y),
          vel: vec2(0, 0),
          baseRadius,
          radius: baseRadius,
          color,
          alpha,
          layer,
          depth,
          phase: Math.random() * Math.PI * 2,
          noiseOffset: vec2(Math.random() * 1000, Math.random() * 1000),
          driftFreq: vec2(
            0.0002 + Math.random() * 0.0005,
            0.0002 + Math.random() * 0.0005
          ),
          driftAmp: vec2(
            (5 + Math.random() * 12) * (0.3 + depth * 0.7),
            (5 + Math.random() * 12) * (0.3 + depth * 0.7)
          ),
        });
      }
    }
    blobs.sort((a, b) => a.layer - b.layer);
    blobsRef.current = blobs;
  }, [shouldReduceAnimations]);

  // ─── Render loop ───────────────────────────────────────────────
  const render = useCallback((time: number, _delta: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    const c = cfgRef.current;
    const { w, h } = sizeRef.current;
    if (w === 0 || h === 0) return;

    const t = timeRef.current++;
    const field = fieldRef.current as MouseField;

    updateMouse();

    // Fade in
    alphaRef.current = Math.min(alphaRef.current + 0.01, 1);

    // Clear with slight trail for fluid feel
    ctx.clearRect(0, 0, w, h);

    const fieldRadSq = c.fieldRadius * c.fieldRadius;
    const noiseTime = t * c.noiseSpeed;
    const blobs = blobsRef.current;

    for (let i = 0; i < blobs.length; i++) {
      const b = blobs[i];

      // ── 1. Organic idle motion ────────────────────────────
      const noise = noiseRef.current;
      const nx = (b.home.x + b.noiseOffset.x) * c.noiseScale + noiseTime * 1.5;
      const ny = (b.home.y + b.noiseOffset.y) * c.noiseScale + noiseTime * 1.2;
      const noiseOffX = noise.fbm(nx, ny, 3) * c.noiseAmplitude * b.depth;
      const noiseOffY = noise.fbm(nx + 100, ny + 100, 3) * c.noiseAmplitude * b.depth;

      const sinOffX = Math.sin(t * b.driftFreq.x + b.phase) * b.driftAmp.x;
      const sinOffY = Math.cos(t * b.driftFreq.y + b.phase) * b.driftAmp.y;

      const idleX = b.home.x + noiseOffX + sinOffX;
      const idleY = b.home.y + noiseOffY + sinOffY;

      // ── 2. Cursor force field ─────────────────────────────
      const dx = b.pos.x - field.smoothedX;
      const dy = b.pos.y - field.smoothedY;
      const distSq = dx * dx + dy * dy;
      const effectiveRadius = c.fieldRadius * (0.4 + b.depth * 0.8);
      const effectiveRadSq = effectiveRadius * effectiveRadius;

      let fx = 0, fy = 0;

      if (distSq < effectiveRadSq * 4 && distSq > 0.1) {
        const dist = Math.sqrt(distSq);
        const distNorm = dist / effectiveRadius;
        const influence = gaussianFalloff(distNorm, c.fieldSigma);
        const speedBoost = 1 + field.speed * c.velocityBoost;
        const forceMag = c.fieldStrength * influence * b.depth * speedBoost;
        const nxDir = dx / dist;
        const nyDir = dy / dist;
        fx = nxDir * forceMag;
        fy = nyDir * forceMag;
        const swirl = influence * c.fieldStrength * 0.12 * b.depth;
        fx += -nyDir * swirl;
        fy += nxDir * swirl;
      }

      // ── 3. Spring to idle target ──────────────────────────
      const toIdleX = idleX - b.pos.x;
      const toIdleY = idleY - b.pos.y;
      const springMul = c.springK * (0.3 + b.depth * 0.7);
      const sfx = toIdleX * springMul;
      const sfy = toIdleY * springMul;

      // ── 4. Physics integration ────────────────────────────
      b.vel.x += fx + sfx;
      b.vel.y += fy + sfy;
      const layerDamping = c.damping - (1 - b.depth) * 0.03;
      b.vel.x *= layerDamping;
      b.vel.y *= layerDamping;
      b.pos.x += b.vel.x;
      b.pos.y += b.vel.y;

      // ── 5. Radius breathing ───────────────────────────────
      const breathe = Math.sin(t * 0.002 * (0.5 + b.depth) + b.phase) * 0.08;
      b.radius = b.baseRadius * (1 + breathe);

      // ── 6. Render ─────────────────────────────────────────
      const sx = b.pos.x;
      const sy = b.pos.y;

      if (sx < -c.maxRadius * 2 || sx > w + c.maxRadius * 2 ||
          sy < -c.maxRadius * 2 || sy > h + c.maxRadius * 2) continue;

      const r = b.radius;
      const a = b.alpha * alphaRef.current;

      // Glow pass
      if (b.layer >= Math.max(cfgRef.current.layerCount - 3, 0) && c.glowIntensity > 0) {
        ctx.save();
        ctx.shadowColor = b.color;
        ctx.shadowBlur = 20 + 30 * b.depth * c.glowIntensity;
        ctx.globalAlpha = a * 0.35;
        ctx.fillStyle = b.color;
        ctx.beginPath();
        ctx.arc(sx, sy, r * 1.1, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      // Main soft blob
      ctx.globalAlpha = a;
      ctx.fillStyle = b.color;

      // Use radial gradient for soft edge
      const grad = ctx.createRadialGradient(sx, sy, 0, sx, sy, r);
      grad.addColorStop(0, b.color);
      grad.addColorStop(0.4, b.color);
      grad.addColorStop(1, 'transparent');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.fill();

      // Center highlight for depth on foreground layers
      if (b.depth > 0.5) {
        ctx.globalAlpha = a * 0.3;
        const hg = ctx.createRadialGradient(
          sx - r * 0.2, sy - r * 0.2, 0,
          sx - r * 0.2, sy - r * 0.2, r * 0.5
        );
        hg.addColorStop(0, 'rgba(255,255,255,0.25)');
        hg.addColorStop(1, 'transparent');
        ctx.fillStyle = hg;
        ctx.beginPath();
        ctx.arc(sx - r * 0.15, sy - r * 0.15, r * 0.5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
  }, [updateMouse]);

  useAnimationEngine(render, !shouldReduceAnimations);

  // ─── Resize ──────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleResize = () => {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      sizeRef.current = { w, h };
      initBlobs(w, h);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [initBlobs]);

  if (shouldReduceAnimations) {
    return (
      <div
        className={`fixed inset-0 w-full h-full pointer-events-none ${className}`}
        style={{
          zIndex: 1,
          background:
            'radial-gradient(ellipse at 30% 50%, rgba(88,130,248,0.06) 0%, transparent 60%), radial-gradient(ellipse at 70% 20%, rgba(139,92,246,0.04) 0%, transparent 50%)',
          ...style,
        }}
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

export default KuroBackground;
