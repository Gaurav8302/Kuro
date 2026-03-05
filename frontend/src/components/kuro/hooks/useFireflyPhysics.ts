/**
 * Firefly Physics Engine
 * 
 * Uses spring physics with organic noise to create a living cursor replacement.
 * All calculations happen in refs - zero React re-renders per frame.
 */

import { useRef, useCallback, useEffect } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
// TUNING CONSTANTS - Adjust these for feel
// ═══════════════════════════════════════════════════════════════════════════

export const FIREFLY_CONFIG = {
  // Spring physics
  SPRING_STIFFNESS: 0.08,      // How quickly it catches up (0.05-0.15 range)
  SPRING_DAMPING: 0.82,        // Friction (0.8-0.95, higher = more floaty)
  
  // Organic drift
  DRIFT_INTENSITY: 0.3,        // Random movement when idle (pixels)
  DRIFT_FREQUENCY: 0.002,      // How often drift changes direction
  
  // Visual
  BASE_SIZE: 6,                // Core size in pixels
  GLOW_SIZE: 20,               // Outer glow radius
  FLICKER_SPEED: 0.05,         // Opacity oscillation speed
  FLICKER_INTENSITY: 0.15,     // How much opacity varies (0-1)
  
  // Trail
  TRAIL_LENGTH: 8,             // Number of trail particles
  TRAIL_DECAY: 0.85,           // Each trail point is this % of previous
  
  // Escape behavior (when fleeing bot)
  ESCAPE_BOOST: 2.5,           // Velocity multiplier when escaping
  ESCAPE_DURATION: 300,        // ms of boosted movement
  
  // Catch state
  RESPAWN_DELAY: 1500,         // ms before firefly respawns after catch
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

export interface FireflyState {
  // Position
  x: number;
  y: number;
  // Velocity
  vx: number;
  vy: number;
  // Visual state
  opacity: number;
  scale: number;
  // Trail positions (for motion blur effect)
  trail: Array<{ x: number; y: number; opacity: number }>;
  // State flags
  isCaught: boolean;
  isEscaping: boolean;
  escapeEndTime: number;
}

export interface FireflyControls {
  getState: () => FireflyState;
  triggerEscape: () => void;
  triggerCatch: (botX: number, botY: number) => void;
  respawn: (x: number, y: number) => void;
}

// ═══════════════════════════════════════════════════════════════════════════
// SIMPLEX NOISE (lightweight, no dependencies)
// ═══════════════════════════════════════════════════════════════════════════

// Simple pseudo-random noise for organic drift
function noise(t: number, seed: number = 0): number {
  const x = Math.sin(t * 1.1 + seed) * 43758.5453;
  return (x - Math.floor(x)) * 2 - 1; // Returns -1 to 1
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN HOOK
// ═══════════════════════════════════════════════════════════════════════════

export function useFireflyPhysics(): FireflyControls {
  // All state lives in refs - no React renders
  const stateRef = useRef<FireflyState>({
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    opacity: 0.9,
    scale: 1,
    trail: [],
    isCaught: false,
    isEscaping: false,
    escapeEndTime: 0,
  });

  const targetRef = useRef({ x: 0, y: 0 }); // Actual cursor position
  const timeRef = useRef(0);
  const frameRef = useRef<number>(0);
  const isActiveRef = useRef(true);

  // Initialize trail
  useEffect(() => {
    stateRef.current.trail = Array(FIREFLY_CONFIG.TRAIL_LENGTH).fill(null).map(() => ({
      x: 0,
      y: 0,
      opacity: 0,
    }));
  }, []);

  // Mouse tracking (raw position, no physics here)
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      targetRef.current.x = e.clientX;
      targetRef.current.y = e.clientY;
      
      // Initialize position on first move
      if (stateRef.current.x === 0 && stateRef.current.y === 0) {
        stateRef.current.x = e.clientX;
        stateRef.current.y = e.clientY;
      }
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Main physics loop
  useEffect(() => {
    const tick = (timestamp: number) => {
      if (!isActiveRef.current) return;
      
      const state = stateRef.current;
      const target = targetRef.current;
      const config = FIREFLY_CONFIG;
      
      timeRef.current = timestamp;

      // Skip if caught (will be absorbed into bot)
      if (state.isCaught) {
        frameRef.current = requestAnimationFrame(tick);
        return;
      }

      // ─────────────────────────────────────────────────────────────────────
      // SPRING PHYSICS
      // ─────────────────────────────────────────────────────────────────────
      
      const dx = target.x - state.x;
      const dy = target.y - state.y;
      
      // Spring force
      let ax = dx * config.SPRING_STIFFNESS;
      let ay = dy * config.SPRING_STIFFNESS;

      // ─────────────────────────────────────────────────────────────────────
      // ORGANIC DRIFT (never perfectly still)
      // ─────────────────────────────────────────────────────────────────────
      
      const driftX = noise(timestamp * config.DRIFT_FREQUENCY, 0) * config.DRIFT_INTENSITY;
      const driftY = noise(timestamp * config.DRIFT_FREQUENCY, 100) * config.DRIFT_INTENSITY;
      
      ax += driftX;
      ay += driftY;

      // ─────────────────────────────────────────────────────────────────────
      // ESCAPE BOOST (when fleeing from bot)
      // ─────────────────────────────────────────────────────────────────────
      
      if (state.isEscaping && timestamp < state.escapeEndTime) {
        // Boost acceleration away from current velocity direction
        ax *= config.ESCAPE_BOOST;
        ay *= config.ESCAPE_BOOST;
      } else if (state.isEscaping) {
        state.isEscaping = false;
      }

      // ─────────────────────────────────────────────────────────────────────
      // VELOCITY UPDATE
      // ─────────────────────────────────────────────────────────────────────
      
      state.vx += ax;
      state.vy += ay;
      
      // Apply damping
      state.vx *= config.SPRING_DAMPING;
      state.vy *= config.SPRING_DAMPING;
      
      // Update position
      state.x += state.vx;
      state.y += state.vy;

      // ─────────────────────────────────────────────────────────────────────
      // VISUAL FLICKER
      // ─────────────────────────────────────────────────────────────────────
      
      const flickerNoise = noise(timestamp * config.FLICKER_SPEED, 200);
      state.opacity = 0.85 + flickerNoise * config.FLICKER_INTENSITY;
      state.scale = 1 + flickerNoise * 0.1;

      // ─────────────────────────────────────────────────────────────────────
      // TRAIL UPDATE (motion blur illusion)
      // ─────────────────────────────────────────────────────────────────────
      
      // Shift trail positions
      for (let i = state.trail.length - 1; i > 0; i--) {
        state.trail[i].x = state.trail[i - 1].x;
        state.trail[i].y = state.trail[i - 1].y;
        state.trail[i].opacity = state.trail[i - 1].opacity * config.TRAIL_DECAY;
      }
      
      // Add current position to trail head
      if (state.trail.length > 0) {
        state.trail[0].x = state.x;
        state.trail[0].y = state.y;
        state.trail[0].opacity = 0.4;
      }

      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);
    
    return () => {
      isActiveRef.current = false;
      cancelAnimationFrame(frameRef.current);
    };
  }, []);

  // ─────────────────────────────────────────────────────────────────────────
  // CONTROL METHODS
  // ─────────────────────────────────────────────────────────────────────────

  const getState = useCallback((): FireflyState => {
    return stateRef.current;
  }, []);

  const triggerEscape = useCallback(() => {
    const state = stateRef.current;
    state.isEscaping = true;
    state.escapeEndTime = performance.now() + FIREFLY_CONFIG.ESCAPE_DURATION;
    
    // Brief glow spike
    state.opacity = 1;
    state.scale = 1.3;
  }, []);

  const triggerCatch = useCallback((botX: number, botY: number) => {
    const state = stateRef.current;
    state.isCaught = true;
    
    // Move to bot center for absorption effect
    state.x = botX;
    state.y = botY;
    state.vx = 0;
    state.vy = 0;
    state.opacity = 0;
  }, []);

  const respawn = useCallback((x: number, y: number) => {
    const state = stateRef.current;
    state.isCaught = false;
    state.x = x;
    state.y = y;
    state.vx = 0;
    state.vy = 0;
    state.opacity = 0; // Fade in
    state.scale = 0.5; // Scale up
    
    // Clear trail
    state.trail.forEach(t => {
      t.x = x;
      t.y = y;
      t.opacity = 0;
    });
  }, []);

  return { getState, triggerEscape, triggerCatch, respawn };
}
