import React, { memo, useEffect, useRef } from 'react';
import type { CoreMode, MemoryNode } from './types';
import type { PointerState } from './ExperienceContext';

/**
 * KuroCore — the persistent visual anchor.
 *
 * An abstract "memory lattice": a soft luminous centre, a thin inclined orbit
 * of fine points, and — once Kuro knows something about you — inner nodes
 * connected to the centre. It is drawn on a 2D canvas (no WebGL) at a fixed
 * base resolution and scaled by the environment, so the same object moves
 * from stage to stage instead of being recreated.
 *
 * Modes are continuous: parameters ease toward their targets, so switching
 * from idle → thinking → responding reads as one object changing state.
 *
 * Performance: ~60 points, one gradient, a handful of hairlines. The loop
 * pauses when the tab is hidden, throttles when idle, and is a single static
 * paint under prefers-reduced-motion.
 */

export const CORE_BASE = 320;

interface KuroCoreProps {
  mode: CoreMode;
  nodes: MemoryNode[];
  /** On-screen size in px (used to keep hairlines ~1px regardless of scale) */
  targetSize: number;
  pointer?: React.MutableRefObject<PointerState>;
  interactive?: boolean;
  reducedMotion?: boolean;
  className?: string;
}

interface ModeParams {
  omega: number; // orbit angular speed (rad/s)
  ring: number; // ring radius factor
  centre: number; // centre alpha
  glow: number; // halo alpha
  points: number; // ring point alpha multiplier
  wave: number; // thinking wave strength 0..1
  nodes: number; // memory node visibility 0..1
}

const MODE_TARGETS: Record<CoreMode, ModeParams> = {
  idle: { omega: (Math.PI * 2) / 96, ring: 1.0, centre: 0.82, glow: 0.1, points: 0.7, wave: 0, nodes: 1 },
  attention: { omega: (Math.PI * 2) / 44, ring: 0.95, centre: 0.95, glow: 0.14, points: 0.95, wave: 0, nodes: 1 },
  thinking: { omega: (Math.PI * 2) / 9, ring: 0.9, centre: 1.0, glow: 0.18, points: 0.75, wave: 1, nodes: 1 },
  responding: { omega: (Math.PI * 2) / 30, ring: 1.08, centre: 1.0, glow: 0.2, points: 1.0, wave: 0, nodes: 1 },
  connecting: { omega: (Math.PI * 2) / 18, ring: 0.78, centre: 1.0, glow: 0.16, points: 1.0, wave: 0.35, nodes: 0 },
  genesis: { omega: (Math.PI * 2) / 34, ring: 1.0, centre: 0.95, glow: 0.16, points: 0.8, wave: 0, nodes: 1 },
};

interface LiveNode {
  id: string;
  born: number; // ms
  seed: number;
}

function readHsl(varName: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return v || fallback;
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

export const KuroCore = memo<KuroCoreProps>(function KuroCore({
  mode,
  nodes,
  targetSize,
  pointer,
  interactive = false,
  reducedMotion = false,
  className,
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const modeRef = useRef<CoreMode>(mode);
  const modeSince = useRef<number>(performance.now());
  const targetRef = useRef(targetSize);
  const interactiveRef = useRef(interactive);
  const liveNodes = useRef<LiveNode[]>([]);
  const nodesRef = useRef(nodes);

  modeRef.current = mode;
  targetRef.current = targetSize;
  interactiveRef.current = interactive;

  // Track node arrivals so they can be seen joining the lattice.
  useEffect(() => {
    const now = performance.now();
    const existing = new Map(liveNodes.current.map((n) => [n.id, n]));
    const next: LiveNode[] = nodes.slice(0, 14).map((n, i) => {
      const prev = existing.get(n.id);
      return prev ?? { id: n.id, born: now + i * 40, seed: (hash(n.id) % 1000) / 1000 };
    });
    liveNodes.current = next;
    nodesRef.current = nodes;
  }, [nodes]);

  useEffect(() => {
    modeSince.current = performance.now();
  }, [mode]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = CORE_BASE * dpr;
    canvas.height = CORE_BASE * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const primary = readHsl('--primary', '186 34% 72%');
    const foreground = readHsl('--foreground', '220 14% 90%');
    const hsla = (hsl: string, a: number) => `hsl(${hsl} / ${a})`;

    const N = 56;
    const R = (CORE_BASE / 2) * 0.92;
    const cx = CORE_BASE / 2;
    const cy = CORE_BASE / 2;

    // Eased state
    const p: ModeParams = { ...MODE_TARGETS[modeRef.current] };
    let theta = 0;
    let tiltX = 0; // pointer lean
    let tiltY = 0;
    let breathe = 0;
    let last = performance.now();
    let raf = 0;
    let running = true;
    let lastPaint = 0;

    const draw = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;

      // --- ease parameters toward the current mode ---
      const target = MODE_TARGETS[modeRef.current];
      const k = 1 - Math.exp(-dt * 4.5);
      p.omega = lerp(p.omega, target.omega, k);
      p.ring = lerp(p.ring, target.ring, k);
      p.centre = lerp(p.centre, target.centre, k);
      p.glow = lerp(p.glow, target.glow, k);
      p.points = lerp(p.points, target.points, k);
      p.wave = lerp(p.wave, target.wave, k);
      p.nodes = lerp(p.nodes, target.nodes, k);

      theta += p.omega * dt;
      breathe += dt;

      // --- pointer presence (leans the orbit; calms when still) ---
      let px = 0;
      let py = 0;
      if (interactiveRef.current && pointer?.current.active) {
        const idle = now - pointer.current.lastMove;
        const fade = idle > 2600 ? Math.max(0, 1 - (idle - 2600) / 2400) : 1;
        px = pointer.current.x * fade;
        py = pointer.current.y * fade;
      }
      const kp = 1 - Math.exp(-dt * 3);
      tiltX = lerp(tiltX, px, kp);
      tiltY = lerp(tiltY, py, kp);

      // Responding: one soft expansion then settle.
      let pulse = 0;
      if (modeRef.current === 'responding') {
        const t = Math.min(1, (now - modeSince.current) / 1000);
        pulse = Math.sin(Math.PI * t) * 0.08;
      }

      const size = targetRef.current || CORE_BASE;
      const unit = CORE_BASE / Math.max(size, 12); // canvas px per on-screen px
      const compact = size < 64;
      const breatheF = 1 + 0.012 * Math.sin(breathe / 4.6);
      const ringR = R * 0.72 * p.ring * breatheF * (1 + pulse);

      ctx.clearRect(0, 0, CORE_BASE, CORE_BASE);

      // --- halo ---
      const haloR = R * 0.62;
      const halo = ctx.createRadialGradient(cx, cy, 0, cx, cy, haloR);
      halo.addColorStop(0, hsla(primary, p.glow * 0.9));
      halo.addColorStop(0.55, hsla(primary, p.glow * 0.18));
      halo.addColorStop(1, hsla(primary, 0));
      ctx.fillStyle = halo;
      ctx.beginPath();
      ctx.arc(cx, cy, haloR, 0, Math.PI * 2);
      ctx.fill();

      // --- centre ---
      const cR = R * (compact ? 0.2 : 0.16) * (1 + (modeRef.current === 'thinking' ? 0.02 * Math.sin(now / 160) : 0));
      const core = ctx.createRadialGradient(cx - cR * 0.15, cy - cR * 0.15, cR * 0.1, cx, cy, cR);
      core.addColorStop(0, hsla(foreground, Math.min(1, p.centre)));
      core.addColorStop(0.5, hsla(primary, p.centre * 0.9));
      core.addColorStop(1, hsla(primary, 0));
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(cx, cy, cR, 0, Math.PI * 2);
      ctx.fill();

      // --- orbit ring ---
      const squash = 0.36 + tiltY * 0.09;
      const lean = tiltX * 0.28;
      const cosL = Math.cos(lean);
      const sinL = Math.sin(lean);
      const count = compact ? 16 : N;
      const waveTheta = now / 260;
      const pr = Math.max(0.9, 1.15 * unit) / unit; // on-screen ~1.15px → canvas units
      for (let i = 0; i < count; i++) {
        const a = theta + (i / count) * Math.PI * 2;
        const ex = Math.cos(a) * ringR;
        const ey = Math.sin(a) * ringR * squash;
        const depth = (Math.sin(a) + 1) / 2; // 0 back .. 1 front
        const x = cx + ex * cosL - ey * sinL;
        const y = cy + ex * sinL + ey * cosL;
        let alpha = (0.18 + depth * 0.62) * p.points;
        if (p.wave > 0) {
          const w = Math.max(0, Math.cos(a - waveTheta));
          alpha += w * w * 0.6 * p.wave;
        }
        const r = (pr * unit) * (0.7 + depth * 0.7);
        ctx.fillStyle = hsla(foreground, Math.min(1, alpha));
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }

      // --- ring hairline (very faint, reads as a plane) ---
      if (!compact) {
        ctx.strokeStyle = hsla(foreground, 0.06 * p.points);
        ctx.lineWidth = 1 * unit * 0.6;
        ctx.beginPath();
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(lean);
        ctx.scale(1, squash);
        ctx.arc(0, 0, ringR, 0, Math.PI * 2);
        ctx.restore();
        ctx.stroke();
      }

      // --- memory nodes ---
      const live = liveNodes.current;
      if (!compact && live.length > 0 && p.nodes > 0.02) {
        const innerR = R * 0.44 * breatheF;
        const inSquash = 0.62 - tiltY * 0.05;
        const inLean = -0.5 + tiltX * 0.1;
        const cosI = Math.cos(inLean);
        const sinI = Math.sin(inLean);
        const slow = theta * 0.35;
        const pts: Array<{ x: number; y: number; a: number }> = [];
        for (let i = 0; i < live.length; i++) {
          const n = live[i];
          const arrive = Math.min(1, Math.max(0, (now - n.born) / 1100));
          if (arrive <= 0) continue;
          const ease = 1 - Math.pow(1 - arrive, 3);
          const a = slow + (i / live.length) * Math.PI * 2 + n.seed * 0.6;
          const rr = lerp(R * 1.05, innerR, ease);
          const ex = Math.cos(a) * rr;
          const ey = Math.sin(a) * rr * inSquash;
          const x = cx + ex * cosI - ey * sinI;
          const y = cy + ex * sinI + ey * cosI;
          const alpha = ease * p.nodes;
          pts.push({ x, y, a: alpha });

          // connection to the centre
          ctx.strokeStyle = hsla(primary, 0.16 * alpha);
          ctx.lineWidth = 1 * unit * 0.7;
          ctx.beginPath();
          ctx.moveTo(cx, cy);
          ctx.lineTo(x, y);
          ctx.stroke();

          ctx.fillStyle = hsla(primary, 0.95 * alpha);
          ctx.beginPath();
          ctx.arc(x, y, 1.9 * unit * 0.9 + 0.4, 0, Math.PI * 2);
          ctx.fill();
        }
        // neighbour links — memory becomes a structure, not a list
        if (pts.length > 2) {
          ctx.strokeStyle = hsla(primary, 0.09 * p.nodes);
          ctx.lineWidth = 1 * unit * 0.5;
          ctx.beginPath();
          for (let i = 0; i < pts.length; i++) {
            const a = pts[i];
            const b = pts[(i + 1) % pts.length];
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
          }
          ctx.stroke();
        }
      }
    };

    const loop = (now: number) => {
      if (!running) return;
      raf = requestAnimationFrame(loop);
      if (document.hidden) return;

      // Throttle when nothing is happening.
      const calm =
        modeRef.current === 'idle' &&
        (!pointer?.current.active || now - pointer.current.lastMove > 3000) &&
        liveNodes.current.every((n) => now - n.born > 1400);
      const minInterval = calm ? 1000 / 24 : 0;
      if (now - lastPaint < minInterval) return;
      lastPaint = now;
      draw(now);
    };

    if (reducedMotion) {
      // Static: paint the current state once per mode / node change.
      const paintOnce = () => {
        // Snap parameters so there is no easing tail.
        Object.assign(p, MODE_TARGETS[modeRef.current]);
        liveNodes.current.forEach((n) => (n.born = -10000));
        last = performance.now();
        draw(performance.now());
      };
      paintOnce();
      const id = window.setInterval(paintOnce, 400);
      return () => window.clearInterval(id);
    }

    raf = requestAnimationFrame(loop);
    const onVis = () => {
      last = performance.now();
    };
    document.addEventListener('visibilitychange', onVis);
    return () => {
      running = false;
      cancelAnimationFrame(raf);
      document.removeEventListener('visibilitychange', onVis);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reducedMotion]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      aria-hidden="true"
      style={{ width: CORE_BASE, height: CORE_BASE, display: 'block' }}
    />
  );
});

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

export default KuroCore;
