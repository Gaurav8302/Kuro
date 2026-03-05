/**
 * BotLimbs Component
 * 
 * Renders energy tendrils/limbs that emerge from the Kuro bot
 * when in Interest/Attack proximity zones.
 * 
 * Rendered in Canvas 2D overlay, synchronized with Three.js bot position.
 * 
 * Visual style: Abstract energy appendages
 * - NOT humanoid arms
 * - NOT cartoonish tentacles
 * - Ethereal, semi-transparent energy streams
 */

import { useRef, useEffect, forwardRef, useImperativeHandle, useCallback } from 'react';
import { useLimbKinematics, LIMB_CONFIG, type LimbState } from './hooks/useLimbKinematics';

// ═══════════════════════════════════════════════════════════════════════════
// VISUAL CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

const COLORS = {
  primary: '#00bfff',    // Electric blue
  secondary: '#00e5ff',  // Bright cyan-blue
  core: 'rgba(180, 230, 255, 0.95)',  // Light electric core
  glow: '#0080ff',       // Deep electric blue glow
};

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export interface BotLimbsHandle {
  getState: () => LimbState;
  setBotPosition: (x: number, y: number, radius: number) => void;
  setTarget: (x: number, y: number, vx: number, vy: number) => void;
  updateForZone: (zone: string, intensity: number) => void;
  triggerLunge: () => void;
  triggerRetract: () => void;
}

interface BotLimbsProps {
  enabled?: boolean;
}

const BotLimbs = forwardRef<BotLimbsHandle, BotLimbsProps>(
  ({ enabled = true }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationRef = useRef<number>(0);
    const kinematics = useLimbKinematics();

    // Expose controls to parent
    useImperativeHandle(ref, () => ({
      getState: kinematics.getState,
      setBotPosition: kinematics.setBotPosition,
      setTarget: kinematics.setTarget,
      updateForZone: kinematics.updateForZone,
      triggerLunge: kinematics.triggerLunge,
      triggerRetract: kinematics.triggerRetract,
    }), [kinematics]);

    // ─────────────────────────────────────────────────────────────────────────
    // DRAW A SINGLE LIMB
    // ─────────────────────────────────────────────────────────────────────────

    const drawLimb = useCallback((
      ctx: CanvasRenderingContext2D,
      limb: LimbState['limbs'][0],
      index: number,
      botX: number,
      botY: number
    ) => {
      if (limb.extension <= 0.01) return;

      const segments = limb.segments;
      if (segments.length < 2) return;

      const config = LIMB_CONFIG;
      // Both limbs use electric blue (slight variation for depth)
      const color = COLORS.primary;
      const glowColor = COLORS.glow;

      // ─────────────────────────────────────────────────────────────────────
      // DRAW ENERGY STREAM (gradient thickness)
      // ─────────────────────────────────────────────────────────────────────

      ctx.save();
      ctx.globalAlpha = limb.extension * config.GLOW_INTENSITY;

      // Create path through all segments
      ctx.beginPath();
      ctx.moveTo(segments[0].x, segments[0].y);

      // Smooth curve through points
      for (let i = 1; i < segments.length - 1; i++) {
        const xc = (segments[i].x + segments[i + 1].x) / 2;
        const yc = (segments[i].y + segments[i + 1].y) / 2;
        ctx.quadraticCurveTo(segments[i].x, segments[i].y, xc, yc);
      }

      // Last segment
      const last = segments[segments.length - 1];
      const secondLast = segments[segments.length - 2];
      ctx.quadraticCurveTo(secondLast.x, secondLast.y, last.x, last.y);

      // Outer electric glow stroke
      ctx.strokeStyle = glowColor;
      ctx.lineWidth = (config.BASE_THICKNESS + 10) * limb.extension;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.filter = 'blur(12px)';
      ctx.stroke();

      // Mid glow layer
      ctx.filter = 'blur(6px)';
      ctx.strokeStyle = color;
      ctx.lineWidth = (config.BASE_THICKNESS + 4) * limb.extension;
      ctx.stroke();

      // Core stroke - electric bright
      ctx.filter = 'blur(2px)';
      ctx.strokeStyle = COLORS.secondary;
      ctx.lineWidth = config.BASE_THICKNESS * limb.extension;
      ctx.stroke();

      // Inner bright core - white-blue
      ctx.filter = 'none';
      ctx.strokeStyle = COLORS.core;
      ctx.lineWidth = config.TIP_THICKNESS * limb.extension;
      ctx.stroke();

      ctx.restore();

      // ─────────────────────────────────────────────────────────────────────
      // DRAW SEGMENT JOINTS (energy nodes)
      // ─────────────────────────────────────────────────────────────────────

      segments.forEach((seg, i) => {
        // Skip first segment, and reduce nodes
        if (i === 0 || i % 2 !== 0) return;

        const t = i / segments.length;
        const size = (1 - t * 0.6) * 4 * limb.extension;

        ctx.save();
        ctx.globalAlpha = limb.extension * 0.8;

        // Glow
        const gradient = ctx.createRadialGradient(
          seg.x, seg.y, 0,
          seg.x, seg.y, size * 3
        );
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, 'transparent');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(seg.x, seg.y, size * 3, 0, Math.PI * 2);
        ctx.fill();

        // Core
        ctx.fillStyle = COLORS.core;
        ctx.beginPath();
        ctx.arc(seg.x, seg.y, size, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
      });

      // ─────────────────────────────────────────────────────────────────────
      // DRAW TIP (round glowing end)
      // ─────────────────────────────────────────────────────────────────────

      const tip = segments[segments.length - 1];
      const tipSize = 12 * limb.extension;  // Larger round tip

      ctx.save();
      ctx.globalAlpha = limb.extension;

      // Outer tip glow
      const tipGradient = ctx.createRadialGradient(
        tip.x, tip.y, 0,
        tip.x, tip.y, tipSize * 2.5
      );
      tipGradient.addColorStop(0, COLORS.core);
      tipGradient.addColorStop(0.2, COLORS.secondary);
      tipGradient.addColorStop(0.5, COLORS.primary);
      tipGradient.addColorStop(1, 'transparent');

      ctx.fillStyle = tipGradient;
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, tipSize * 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Mid glow ring
      ctx.fillStyle = COLORS.secondary;
      ctx.shadowBlur = 15;
      ctx.shadowColor = COLORS.primary;
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, tipSize * 0.8, 0, Math.PI * 2);
      ctx.fill();

      // Bright core center
      ctx.fillStyle = COLORS.core;
      ctx.shadowBlur = 8;
      ctx.shadowColor = COLORS.core;
      ctx.beginPath();
      ctx.arc(tip.x, tip.y, tipSize * 0.4, 0, Math.PI * 2);
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
      // RENDER FUNCTION
      // ─────────────────────────────────────────────────────────────────────

      const render = () => {
        // Run physics
        kinematics.tick();

        const state = kinematics.getState();

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw all limbs
        state.limbs.forEach((limb, i) => {
          drawLimb(ctx, limb, i, state.botX, state.botY);
        });

        animationRef.current = requestAnimationFrame(render);
      };

      animationRef.current = requestAnimationFrame(render);

      return () => {
        window.removeEventListener('resize', resize);
        cancelAnimationFrame(animationRef.current);
      };
    }, [enabled, kinematics, drawLimb]);

    if (!enabled) return null;

    return (
      <canvas
        ref={canvasRef}
        className="fixed inset-0 pointer-events-none z-[100]"
        style={{
          willChange: 'transform',
          contain: 'strict',
        }}
        aria-hidden="true"
      />
    );
  }
);

BotLimbs.displayName = 'BotLimbs';

export default BotLimbs;
