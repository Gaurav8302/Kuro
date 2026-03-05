/**
 * FireflyCursor Component
 * 
 * Replaces system cursor with an organic, glowing firefly entity.
 * Renders via Canvas 2D for maximum performance.
 * 
 * Features:
 * - Spring physics following
 * - Organic drift (never perfectly still)
 * - Subtle flicker and scale variation
 * - Motion trail (blur illusion)
 * - Escape/catch state handling
 */

import { useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { useFireflyPhysics, FIREFLY_CONFIG, type FireflyState } from './hooks/useFireflyPhysics';

// ═══════════════════════════════════════════════════════════════════════════
// VISUAL CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

const COLORS = {
  // Body colors
  bodyDark: '#2a1810',           // Dark brown body
  bodyLight: '#4a3020',          // Lighter brown accent
  // Glow colors (bioluminescent abdomen)
  glowCore: '#fffde0',           // Warm white-yellow core
  glowInner: 'rgba(255, 240, 120, 0.9)',  // Bright yellow
  glowMid: 'rgba(200, 255, 100, 0.6)',    // Yellow-green
  glowOuter: 'rgba(150, 255, 80, 0.2)',   // Soft green outer
  // Wing colors
  wingFill: 'rgba(200, 220, 255, 0.15)',  // Translucent iridescent
  wingStroke: 'rgba(255, 255, 255, 0.3)', // Subtle edge
};

const FIREFLY_VISUAL = {
  BODY_LENGTH: 8,          // Main body length
  BODY_WIDTH: 4,           // Body width
  HEAD_SIZE: 3,            // Head radius
  ABDOMEN_SIZE: 5,         // Glowing abdomen size
  WING_LENGTH: 10,         // Wing length
  WING_WIDTH: 4,           // Wing width at base
  WING_FLUTTER_SPEED: 0.15, // Wing animation speed
  WING_FLUTTER_AMOUNT: 0.3, // How much wings move
};

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export interface FireflyCursorHandle {
  getState: () => FireflyState;
  triggerEscape: () => void;
  triggerCatch: (botX: number, botY: number) => void;
  respawn: (x: number, y: number) => void;
}

interface FireflyCursorProps {
  enabled?: boolean;
}

const FireflyCursor = forwardRef<FireflyCursorHandle, FireflyCursorProps>(
  ({ enabled = true }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const animationRef = useRef<number>(0);
    const physics = useFireflyPhysics();

    // Expose controls to parent
    useImperativeHandle(ref, () => ({
      getState: physics.getState,
      triggerEscape: physics.triggerEscape,
      triggerCatch: physics.triggerCatch,
      respawn: physics.respawn,
    }), [physics]);

    // ─────────────────────────────────────────────────────────────────────────
    // CURSOR HIDING
    // ─────────────────────────────────────────────────────────────────────────

    useEffect(() => {
      if (!enabled) return;

      // Hide system cursor on landing page
      document.body.style.cursor = 'none';
      
      // Also hide on all interactive elements
      const style = document.createElement('style');
      style.id = 'firefly-cursor-hide';
      style.textContent = `
        *, *::before, *::after {
          cursor: none !important;
        }
      `;
      document.head.appendChild(style);

      return () => {
        document.body.style.cursor = '';
        const existingStyle = document.getElementById('firefly-cursor-hide');
        if (existingStyle) existingStyle.remove();
      };
    }, [enabled]);

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
        ctx.scale(dpr, dpr);
      };

      resize();
      window.addEventListener('resize', resize, { passive: true });

      // ─────────────────────────────────────────────────────────────────────
      // RENDER FUNCTION
      // ─────────────────────────────────────────────────────────────────────

      let frameCount = 0;

      const render = () => {
        const state = physics.getState();
        frameCount++;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Don't render if caught
        if (state.isCaught) {
          animationRef.current = requestAnimationFrame(render);
          return;
        }

        // Calculate movement angle for orientation
        const speed = Math.sqrt(state.vx * state.vx + state.vy * state.vy);
        const angle = speed > 0.5 ? Math.atan2(state.vy, state.vx) : 0;
        
        // Wing flutter animation
        const wingFlutter = Math.sin(frameCount * FIREFLY_VISUAL.WING_FLUTTER_SPEED) * FIREFLY_VISUAL.WING_FLUTTER_AMOUNT;

        // ─────────────────────────────────────────────────────────────────────
        // DRAW GLOW TRAIL
        // ─────────────────────────────────────────────────────────────────────

        state.trail.forEach((point, i) => {
          if (point.opacity < 0.02) return;
          
          const size = FIREFLY_VISUAL.ABDOMEN_SIZE * (1 - i / state.trail.length) * 0.6;
          
          ctx.save();
          ctx.globalAlpha = point.opacity * state.opacity * 0.5;
          
          const trailGradient = ctx.createRadialGradient(
            point.x, point.y, 0,
            point.x, point.y, size * 2
          );
          trailGradient.addColorStop(0, COLORS.glowInner);
          trailGradient.addColorStop(0.5, COLORS.glowMid);
          trailGradient.addColorStop(1, 'transparent');
          
          ctx.fillStyle = trailGradient;
          ctx.beginPath();
          ctx.arc(point.x, point.y, size * 2, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        });

        ctx.save();
        ctx.translate(state.x, state.y);
        ctx.rotate(angle);
        ctx.globalAlpha = state.opacity;

        // ─────────────────────────────────────────────────────────────────────
        // DRAW WINGS (translucent, fluttering)
        // ─────────────────────────────────────────────────────────────────────

        const wingY = FIREFLY_VISUAL.WING_WIDTH * (0.8 + wingFlutter);
        
        // Left wing
        ctx.save();
        ctx.globalAlpha = state.opacity * 0.4;
        ctx.fillStyle = COLORS.wingFill;
        ctx.strokeStyle = COLORS.wingStroke;
        ctx.lineWidth = 0.5;
        
        ctx.beginPath();
        ctx.ellipse(
          -FIREFLY_VISUAL.BODY_LENGTH * 0.2,  // x offset (slightly back)
          -wingY,                               // y offset (above body)
          FIREFLY_VISUAL.WING_LENGTH,          // radiusX
          FIREFLY_VISUAL.WING_WIDTH,           // radiusY
          -0.3 + wingFlutter * 0.5,            // rotation
          0, Math.PI * 2
        );
        ctx.fill();
        ctx.stroke();
        
        // Right wing
        ctx.beginPath();
        ctx.ellipse(
          -FIREFLY_VISUAL.BODY_LENGTH * 0.2,
          wingY,
          FIREFLY_VISUAL.WING_LENGTH,
          FIREFLY_VISUAL.WING_WIDTH,
          0.3 - wingFlutter * 0.5,
          0, Math.PI * 2
        );
        ctx.fill();
        ctx.stroke();
        ctx.restore();

        // ─────────────────────────────────────────────────────────────────────
        // DRAW BODY (head, thorax, abdomen)
        // ─────────────────────────────────────────────────────────────────────

        // Head (front)
        ctx.fillStyle = COLORS.bodyDark;
        ctx.beginPath();
        ctx.arc(
          FIREFLY_VISUAL.BODY_LENGTH * 0.5,
          0,
          FIREFLY_VISUAL.HEAD_SIZE,
          0, Math.PI * 2
        );
        ctx.fill();

        // Thorax (middle body)
        ctx.fillStyle = COLORS.bodyLight;
        ctx.beginPath();
        ctx.ellipse(
          0, 0,
          FIREFLY_VISUAL.BODY_LENGTH * 0.4,
          FIREFLY_VISUAL.BODY_WIDTH,
          0, 0, Math.PI * 2
        );
        ctx.fill();

        // ─────────────────────────────────────────────────────────────────────
        // DRAW GLOWING ABDOMEN (bioluminescent part)
        // ─────────────────────────────────────────────────────────────────────

        const abdomenX = -FIREFLY_VISUAL.BODY_LENGTH * 0.6;
        const abdomenSize = FIREFLY_VISUAL.ABDOMEN_SIZE * state.scale;

        // Outer glow
        const outerGlow = ctx.createRadialGradient(
          abdomenX, 0, 0,
          abdomenX, 0, abdomenSize * 3
        );
        outerGlow.addColorStop(0, COLORS.glowInner);
        outerGlow.addColorStop(0.3, COLORS.glowMid);
        outerGlow.addColorStop(0.6, COLORS.glowOuter);
        outerGlow.addColorStop(1, 'transparent');

        ctx.save();
        ctx.globalAlpha = state.opacity * 0.8;
        ctx.fillStyle = outerGlow;
        ctx.beginPath();
        ctx.arc(abdomenX, 0, abdomenSize * 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // Inner glow
        const innerGlow = ctx.createRadialGradient(
          abdomenX, 0, 0,
          abdomenX, 0, abdomenSize * 1.5
        );
        innerGlow.addColorStop(0, COLORS.glowCore);
        innerGlow.addColorStop(0.5, COLORS.glowInner);
        innerGlow.addColorStop(1, COLORS.glowMid);

        ctx.fillStyle = innerGlow;
        ctx.beginPath();
        ctx.ellipse(
          abdomenX, 0,
          abdomenSize * 1.2,
          abdomenSize,
          0, 0, Math.PI * 2
        );
        ctx.fill();

        // Core (brightest point)
        ctx.fillStyle = COLORS.glowCore;
        ctx.shadowBlur = 8;
        ctx.shadowColor = COLORS.glowInner;
        ctx.beginPath();
        ctx.arc(abdomenX, 0, abdomenSize * 0.4, 0, Math.PI * 2);
        ctx.fill();

        // Antennae (small lines from head)
        ctx.strokeStyle = COLORS.bodyDark;
        ctx.lineWidth = 1;
        ctx.lineCap = 'round';
        
        const headX = FIREFLY_VISUAL.BODY_LENGTH * 0.5;
        ctx.beginPath();
        ctx.moveTo(headX + 2, -1);
        ctx.lineTo(headX + 6, -4);
        ctx.moveTo(headX + 2, 1);
        ctx.lineTo(headX + 6, 4);
        ctx.stroke();

        ctx.restore();

        animationRef.current = requestAnimationFrame(render);
      };

      animationRef.current = requestAnimationFrame(render);

      return () => {
        window.removeEventListener('resize', resize);
        cancelAnimationFrame(animationRef.current);
      };
    }, [enabled, physics]);

    if (!enabled) return null;

    return (
      <canvas
        ref={canvasRef}
        className="fixed inset-0 pointer-events-none z-[9999]"
        style={{ 
          willChange: 'transform',
          contain: 'strict',
        }}
        aria-hidden="true"
      />
    );
  }
);

FireflyCursor.displayName = 'FireflyCursor';

export default FireflyCursor;
