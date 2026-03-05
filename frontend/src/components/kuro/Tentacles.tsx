/**
 * Tentacles Component v3 — Depth-Aware Constraint-Based Renderer
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 * DEPTH LAYERING STRATEGY
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * To create the illusion that tentacles emerge from BEHIND the bot:
 * 
 * 1. We use canvas compositing to mask tentacle bases that overlap the bot
 * 2. The render order is:
 *    a) Draw tentacle strands (full length)
 *    b) Apply circular mask at bot position (destination-out)
 *    c) Draw tentacle tips that extend BEYOND the mask
 * 
 * This creates the visual effect of:
 *    - Tentacle bases appearing to emerge from behind the bot body
 *    - Tentacle mid-sections partially occluded by bot silhouette
 *    - Tentacle tips free to move in front (when extended far enough)
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 * VISUAL STYLE
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * - Color: Pure electric blue (#00bfff) — NO gradients, NO rainbow
 * - Shape: Smooth energy strand with slight taper
 * - Tip: Rounded energy bulb OR minimal abstract claw (2-3 prongs)
 * - Glow: Subtle outer glow, intensifies slightly on stretch
 * 
 * This is TECH, not biology.
 */

import { useRef, useEffect, forwardRef, useImperativeHandle, useCallback } from 'react';
import { 
  useTentacleSystem, 
  getTentacleCurve,
  TENTACLE_CONFIG,
  type Tentacle,
  type TentacleControls 
} from './hooks/useTentacleSystem';

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

export interface TentaclesHandle {
  setBotPosition: (x: number, y: number, radius: number) => void;
  checkProximity: (cursorX: number, cursorY: number) => void;
}

interface TentaclesProps {
  enabled?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

const Tentacles = forwardRef<TentaclesHandle, TentaclesProps>(
  ({ enabled = true }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationRef = useRef<number>(0);
    const system = useTentacleSystem();

    // Expose controls to parent
    useImperativeHandle(ref, () => ({
      setBotPosition: system.setBotPosition,
      checkProximity: system.checkProximity,
    }), [system]);

    // ─────────────────────────────────────────────────────────────────────────
    // DRAW TAPERED STROKE (thickness varies along path)
    // ─────────────────────────────────────────────────────────────────────────

    const drawTaperedStroke = useCallback((
      ctx: CanvasRenderingContext2D,
      points: { x: number; y: number }[],
      baseThickness: number,
      tipThickness: number,
      color: string,
      stretchFactor: number = 1
    ) => {
      if (points.length < 2) return;

      // Apply stretch thinning
      const stretchThinning = 1 - (1 - TENTACLE_CONFIG.STRETCH_THINNING) * stretchFactor;
      baseThickness *= stretchThinning;
      tipThickness *= stretchThinning;

      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      // Draw segments with varying thickness
      for (let i = 0; i < points.length - 1; i++) {
        const t = i / (points.length - 1);
        const thickness = baseThickness + (tipThickness - baseThickness) * t;
        
        ctx.beginPath();
        ctx.moveTo(points[i].x, points[i].y);
        ctx.lineTo(points[i + 1].x, points[i + 1].y);
        ctx.strokeStyle = color;
        ctx.lineWidth = thickness;
        ctx.stroke();
      }
    }, []);

    // ─────────────────────────────────────────────────────────────────────────
    // DRAW SINGLE TENTACLE (with depth masking)
    // ─────────────────────────────────────────────────────────────────────────

    const drawTentacle = useCallback((
      ctx: CanvasRenderingContext2D,
      tentacle: Tentacle,
      points: { x: number; y: number }[],
      botX: number,
      botY: number,
      botRadius: number
    ) => {
      if (points.length < 2 || tentacle.extension <= 0.01) return;

      const config = TENTACLE_CONFIG;
      const stretchFactor = tentacle.stretchAmount;
      
      ctx.save();
      
      // Fade based on extension
      ctx.globalAlpha = Math.min(tentacle.extension * 1.2, 1);

      // ─────────────────────────────────────────────────────────────────────
      // LAYER 1: OUTER GLOW (drawn first, behind everything)
      // ─────────────────────────────────────────────────────────────────────

      ctx.filter = 'blur(12px)';
      drawTaperedStroke(
        ctx,
        points,
        config.BASE_THICKNESS + 12,
        config.TIP_THICKNESS + 8,
        config.GLOW_COLOR,
        stretchFactor
      );

      // ─────────────────────────────────────────────────────────────────────
      // LAYER 2: MAIN STRAND
      // ─────────────────────────────────────────────────────────────────────

      ctx.filter = 'blur(2px)';
      drawTaperedStroke(
        ctx,
        points,
        config.BASE_THICKNESS,
        config.TIP_THICKNESS,
        config.COLOR,
        stretchFactor
      );

      // ─────────────────────────────────────────────────────────────────────
      // LAYER 3: BRIGHT CORE
      // ─────────────────────────────────────────────────────────────────────

      ctx.filter = 'none';
      drawTaperedStroke(
        ctx,
        points,
        config.BASE_THICKNESS * 0.35,
        config.TIP_THICKNESS * 0.35,
        config.CORE_COLOR,
        stretchFactor
      );

      // ─────────────────────────────────────────────────────────────────────
      // LAYER 4: TIP GLOW (energy bulb)
      // ─────────────────────────────────────────────────────────────────────

      const tip = points[points.length - 1];
      const tipSize = (config.TIP_THICKNESS * 0.8) * (1 + stretchFactor * 0.3);

      // Outer tip glow
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, tipSize * 2, 0, Math.PI * 2);
      ctx.fillStyle = config.GLOW_COLOR;
      ctx.filter = 'blur(8px)';
      ctx.fill();

      // Solid tip
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, tipSize, 0, Math.PI * 2);
      ctx.fillStyle = config.COLOR;
      ctx.filter = 'blur(1px)';
      ctx.fill();

      // Bright tip center
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, tipSize * 0.5, 0, Math.PI * 2);
      ctx.fillStyle = config.CORE_COLOR;
      ctx.filter = 'none';
      ctx.fill();

      ctx.restore();
    }, [drawTaperedStroke]);

    // ─────────────────────────────────────────────────────────────────────────
    // APPLY BOT MASK (creates depth illusion)
    // ─────────────────────────────────────────────────────────────────────────

    const applyBotMask = useCallback((
      ctx: CanvasRenderingContext2D,
      botX: number,
      botY: number,
      botRadius: number
    ) => {
      // Use destination-out to cut a hole where the bot is
      // This makes tentacle bases appear to be behind the bot
      ctx.save();
      ctx.globalCompositeOperation = 'destination-out';
      
      // Create elliptical mask (bot is slightly oval in 3D view)
      ctx.beginPath();
      ctx.ellipse(
        botX, 
        botY, 
        botRadius * 0.85,  // Slightly smaller than visual bot
        botRadius * 0.9,
        0, 
        0, 
        Math.PI * 2
      );
      
      // Soft edge for natural blend
      const gradient = ctx.createRadialGradient(
        botX, botY, botRadius * 0.6,
        botX, botY, botRadius * 0.9
      );
      gradient.addColorStop(0, 'rgba(0,0,0,1)');
      gradient.addColorStop(0.7, 'rgba(0,0,0,0.8)');
      gradient.addColorStop(1, 'rgba(0,0,0,0)');
      
      ctx.fillStyle = gradient;
      ctx.fill();
      
      ctx.restore();
    }, []);

    // ─────────────────────────────────────────────────────────────────────────
    // CANVAS SETUP & RENDER LOOP
    // ─────────────────────────────────────────────────────────────────────────

    useEffect(() => {
      if (!enabled) return;

      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d', { alpha: true });
      if (!ctx) return;

      // Set canvas size
      const resize = () => {
        const dpr = window.devicePixelRatio || 1;
        canvas.width = window.innerWidth * dpr;
        canvas.height = window.innerHeight * dpr;
        canvas.style.width = `${window.innerWidth}px`;
        canvas.style.height = `${window.innerHeight}px`;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      };

      resize();
      window.addEventListener('resize', resize, { passive: true });

      // ─────────────────────────────────────────────────────────────────────
      // RENDER LOOP
      // ─────────────────────────────────────────────────────────────────────

      const render = (timestamp: number) => {
        // Run state machine
        system.tick(timestamp);

        const state = system.getState();

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Check if any tentacles are visible
        const anyVisible = state.tentacles.some(t => t.extension > 0.01);
        
        if (anyVisible) {
          // ─────────────────────────────────────────────────────────────────
          // STEP 1: Draw all tentacles to an offscreen buffer
          // ─────────────────────────────────────────────────────────────────

          // Draw each tentacle
          state.tentacles.forEach((tentacle) => {
            const points = getTentacleCurve(
              tentacle,
              state.botX,
              state.botY,
              state.botRadius
            );
            drawTentacle(ctx, tentacle, points, state.botX, state.botY, state.botRadius);
          });

          // ─────────────────────────────────────────────────────────────────
          // STEP 2: Apply bot mask to create depth
          // ─────────────────────────────────────────────────────────────────

          applyBotMask(ctx, state.botX, state.botY, state.botRadius);
        }

        animationRef.current = requestAnimationFrame(render);
      };

      animationRef.current = requestAnimationFrame(render);

      return () => {
        window.removeEventListener('resize', resize);
        cancelAnimationFrame(animationRef.current);
      };
    }, [enabled, system, drawTentacle, applyBotMask]);

    if (!enabled) return null;

    return (
      <canvas
        ref={canvasRef}
        className="fixed inset-0 pointer-events-none"
        style={{
          zIndex: 90,  // Behind the bot (bot is z-100+)
          willChange: 'transform',
          contain: 'strict',
        }}
        aria-hidden="true"
      />
    );
  }
);

Tentacles.displayName = 'Tentacles';

export default Tentacles;
