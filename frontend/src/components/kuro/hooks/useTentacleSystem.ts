/**
 * Tentacle System v3 — Constraint-Based Anchored Model
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 * BOT COORDINATE SYSTEM
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 * The bot has an INTERNAL coordinate system:
 *   - Center: (0, 0)
 *   - Radius: R
 *   - Angle 0° = right, 90° = down, 180° = left, 270° = up
 *   - BACK hemisphere: angles 90° < θ < 270° (left half of screen)
 *   - FRONT hemisphere: angles 270° < θ < 90° (right half, toward user)
 * 
 * Tentacle origins are FIXED in back-left and back-right quadrants:
 *   - Left tentacle:  angle ~155°, radius 0.8R (back-upper)
 *   - Right tentacle: angle ~205°, radius 0.8R (back-lower)
 * 
 * These positions are computed ONCE relative to bot center.
 * They move ONLY if the bot moves.
 * 
 * ═══════════════════════════════════════════════════════════════════════════
 * STATE MACHINE
 * ═══════════════════════════════════════════════════════════════════════════
 * 
 *   DORMANT ─────────────────────────────────────────────────────┐
 *      │                                                          │
 *      │ [cursor enters activation zone]                          │
 *      ▼                                                          │
 *   EXTENDING ──────────────────────────────────────────┐         │
 *      │                                                │         │
 *      │ [extension complete + cursor still in zone]    │ [cursor │
 *      ▼                                                │  exits] │
 *   ATTACHED ─────────────────────────────────────────┐ │         │
 *      │                                              │ │         │
 *      │ [cursor moves within stretch limit]          │ │         │
 *      ▼                                              │ │         │
 *   STRETCHED ────────────────────────────────────────┤ │         │
 *      │                                              │ │         │
 *      │ [cursor exceeds max stretch OR exits zone]   │ │         │
 *      ▼                                              ▼ ▼         │
 *   RELEASING ────────────────────────────────────────────────────┘
 *      │
 *      │ [retraction complete]
 *      ▼
 *   DORMANT
 * 
 * CRITICAL: Retraction ONLY happens on:
 *   1. Cursor exceeds max stretch distance
 *   2. Cursor exits activation zone while attached
 *   NEVER on timers. NEVER automatically.
 */

import { useRef, useCallback } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

export const TENTACLE_CONFIG = {
  // ─────────────────────────────────────────────────────────────────────────
  // BOT-RELATIVE ANCHOR POSITIONS (polar coordinates)
  // ─────────────────────────────────────────────────────────────────────────
  
  // Left tentacle: back-upper quadrant (155° from right, 0.8 * radius from center)
  LEFT_ANCHOR_ANGLE: 155 * (Math.PI / 180),   // ~155 degrees
  
  // Right tentacle: back-lower quadrant (205° from right, 0.8 * radius from center)
  RIGHT_ANCHOR_ANGLE: 205 * (Math.PI / 180),  // ~205 degrees
  
  // Both anchors at 80% of bot radius (embedded in back surface)
  ANCHOR_RADIUS_FACTOR: 0.8,
  
  // ─────────────────────────────────────────────────────────────────────────
  // ACTIVATION
  // ─────────────────────────────────────────────────────────────────────────
  
  ACTIVATION_RADIUS: 180,           // Pixels from bot center to trigger
  ATTACH_RADIUS: 80,                // Must get THIS close to attach tip
  
  // ─────────────────────────────────────────────────────────────────────────
  // EXTENSION GEOMETRY
  // ─────────────────────────────────────────────────────────────────────────
  
  // Natural (resting) length as fraction of bot radius
  NATURAL_LENGTH_FACTOR: 0.45,      // 45% of radius = natural reach
  
  // Maximum stretch beyond natural length (15% more)
  MAX_STRETCH_FACTOR: 0.15,         // Can stretch to 115% of natural length
  
  // Number of curve segments for smooth rendering
  SEGMENT_COUNT: 6,
  
  // ─────────────────────────────────────────────────────────────────────────
  // TIMING (in milliseconds)
  // ─────────────────────────────────────────────────────────────────────────
  
  EXTEND_DURATION: 500,             // 500ms extension (deliberate, not snappy)
  RELEASE_DURATION: 350,            // 350ms retraction
  
  // ─────────────────────────────────────────────────────────────────────────
  // PHYSICS (constraint-based, not animation-based)
  // ─────────────────────────────────────────────────────────────────────────
  
  // Tip damping: higher = slower, more resistant feel
  TIP_DAMPING: 0.92,
  TIP_STIFFNESS: 0.04,
  
  // Base is LOCKED - zero movement
  BASE_LOCKED: true,
  
  // ─────────────────────────────────────────────────────────────────────────
  // VISUAL
  // ─────────────────────────────────────────────────────────────────────────
  
  BASE_THICKNESS: 10,               // Thickness at base
  TIP_THICKNESS: 6,                 // Taper toward tip
  COLOR: '#00bfff',                 // Pure electric blue
  CORE_COLOR: '#b3ecff',            // Bright core
  GLOW_COLOR: 'rgba(0, 191, 255, 0.3)',
  
  // Stretched visual cue: slight thinning
  STRETCH_THINNING: 0.85,           // At max stretch, thickness * 0.85
  
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

type TentacleState = 'dormant' | 'extending' | 'attached' | 'stretched' | 'releasing';

interface Vec2 {
  x: number;
  y: number;
}

interface Tentacle {
  // State machine
  state: TentacleState;
  stateStartTime: number;
  
  // Anchor point (calculated from bot position + angle)
  anchorAngle: number;              // Fixed angle in bot's coordinate system
  anchorX: number;                  // Screen position (updated when bot moves)
  anchorY: number;
  
  // Extension
  extension: number;                // 0 = retracted, 1 = fully extended
  
  // Tip position (for attached/stretched states)
  tipX: number;                     // Current tip position
  tipY: number;
  tipTargetX: number;               // Target tip position (cursor when attached)
  tipTargetY: number;
  tipVelX: number;                  // Tip velocity (for damped movement)
  tipVelY: number;
  
  // For releasing state - store initial tip position
  releaseTipStartX: number;
  releaseTipStartY: number;
  
  // Grab direction (fixed at moment of attachment)
  grabDirectionX: number;
  grabDirectionY: number;
  
  // Stretch amount (0 = natural length, 1 = max stretch)
  stretchAmount: number;
  
  // Natural length (computed from bot radius)
  naturalLength: number;
}

interface TentacleSystemState {
  tentacles: [Tentacle, Tentacle];
  botX: number;
  botY: number;
  botRadius: number;
  cursorX: number;
  cursorY: number;
  cursorInZone: boolean;
}

export interface TentacleControls {
  getState: () => TentacleSystemState;
  setBotPosition: (x: number, y: number, radius: number) => void;
  checkProximity: (cursorX: number, cursorY: number) => void;
  tick: (timestamp: number) => void;
}

// ═══════════════════════════════════════════════════════════════════════════
// EASING FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function easeOutQuart(t: number): number {
  return 1 - Math.pow(1 - t, 4);
}

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// ═══════════════════════════════════════════════════════════════════════════
// VECTOR MATH HELPERS
// ═══════════════════════════════════════════════════════════════════════════

function distance(x1: number, y1: number, x2: number, y2: number): number {
  return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
}

function normalize(x: number, y: number): Vec2 {
  const len = Math.sqrt(x * x + y * y);
  if (len < 0.0001) return { x: 1, y: 0 };
  return { x: x / len, y: y / len };
}

// ═══════════════════════════════════════════════════════════════════════════
// CREATE INITIAL TENTACLE
// ═══════════════════════════════════════════════════════════════════════════

function createTentacle(isLeft: boolean): Tentacle {
  const config = TENTACLE_CONFIG;
  const angle = isLeft ? config.LEFT_ANCHOR_ANGLE : config.RIGHT_ANCHOR_ANGLE;
  
  return {
    state: 'dormant',
    stateStartTime: 0,
    anchorAngle: angle,
    anchorX: 0,
    anchorY: 0,
    extension: 0,
    tipX: 0,
    tipY: 0,
    tipTargetX: 0,
    tipTargetY: 0,
    tipVelX: 0,
    tipVelY: 0,
    releaseTipStartX: 0,
    releaseTipStartY: 0,
    grabDirectionX: 0,
    grabDirectionY: 0,
    stretchAmount: 0,
    naturalLength: 100, // Will be recalculated
  };
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN HOOK
// ═══════════════════════════════════════════════════════════════════════════

export function useTentacleSystem(): TentacleControls {
  const stateRef = useRef<TentacleSystemState>({
    tentacles: [createTentacle(true), createTentacle(false)],
    botX: 0,
    botY: 0,
    botRadius: 100,
    cursorX: 0,
    cursorY: 0,
    cursorInZone: false,
  });

  const getState = useCallback(() => stateRef.current, []);

  // ─────────────────────────────────────────────────────────────────────────
  // UPDATE BOT POSITION (and recalculate anchor points)
  // ─────────────────────────────────────────────────────────────────────────

  const setBotPosition = useCallback((x: number, y: number, radius: number) => {
    const state = stateRef.current;
    const config = TENTACLE_CONFIG;
    
    state.botX = x;
    state.botY = y;
    state.botRadius = radius;
    
    // Recalculate anchor positions from polar coordinates
    const anchorRadius = radius * config.ANCHOR_RADIUS_FACTOR;
    
    state.tentacles.forEach(tentacle => {
      tentacle.anchorX = x + Math.cos(tentacle.anchorAngle) * anchorRadius;
      tentacle.anchorY = y + Math.sin(tentacle.anchorAngle) * anchorRadius;
      tentacle.naturalLength = radius * config.NATURAL_LENGTH_FACTOR;
    });
  }, []);

  // ─────────────────────────────────────────────────────────────────────────
  // PROXIMITY CHECK (trigger activation or release)
  // ─────────────────────────────────────────────────────────────────────────

  const checkProximity = useCallback((cursorX: number, cursorY: number) => {
    const state = stateRef.current;
    const config = TENTACLE_CONFIG;
    const now = performance.now();
    
    state.cursorX = cursorX;
    state.cursorY = cursorY;
    
    const dist = distance(cursorX, cursorY, state.botX, state.botY);
    const wasInZone = state.cursorInZone;
    state.cursorInZone = dist < config.ACTIVATION_RADIUS;
    
    // ─────────────────────────────────────────────────────────────────────
    // EDGE DETECTION: Cursor ENTERS zone
    // ─────────────────────────────────────────────────────────────────────
    
    if (state.cursorInZone && !wasInZone) {
      state.tentacles.forEach(tentacle => {
        if (tentacle.state === 'dormant') {
          // Begin extension toward cursor
          tentacle.state = 'extending';
          tentacle.stateStartTime = now;
          
          // Calculate grab direction (fixed at this moment)
          const dx = cursorX - tentacle.anchorX;
          const dy = cursorY - tentacle.anchorY;
          const dir = normalize(dx, dy);
          tentacle.grabDirectionX = dir.x;
          tentacle.grabDirectionY = dir.y;
          
          // Initialize tip at anchor
          tentacle.tipX = tentacle.anchorX;
          tentacle.tipY = tentacle.anchorY;
          tentacle.tipVelX = 0;
          tentacle.tipVelY = 0;
        }
      });
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // EDGE DETECTION: Cursor EXITS zone while attached
    // ─────────────────────────────────────────────────────────────────────
    
    if (!state.cursorInZone && wasInZone) {
      state.tentacles.forEach(tentacle => {
        if (tentacle.state === 'attached' || tentacle.state === 'stretched') {
          tentacle.state = 'releasing';
          tentacle.stateStartTime = now;
          tentacle.releaseTipStartX = tentacle.tipX;
          tentacle.releaseTipStartY = tentacle.tipY;
        }
      });
    }
  }, []);

  // ─────────────────────────────────────────────────────────────────────────
  // MAIN TICK (state machine + physics)
  // ─────────────────────────────────────────────────────────────────────────

  const tick = useCallback((timestamp: number) => {
    const state = stateRef.current;
    const config = TENTACLE_CONFIG;

    state.tentacles.forEach(tentacle => {
      const elapsed = timestamp - tentacle.stateStartTime;

      switch (tentacle.state) {
        // ─────────────────────────────────────────────────────────────────
        // DORMANT: Waiting for activation
        // ─────────────────────────────────────────────────────────────────
        case 'dormant':
          tentacle.extension = 0;
          tentacle.stretchAmount = 0;
          break;

        // ─────────────────────────────────────────────────────────────────
        // EXTENDING: Moving tip toward grab direction
        // ─────────────────────────────────────────────────────────────────
        case 'extending': {
          const progress = Math.min(elapsed / config.EXTEND_DURATION, 1);
          tentacle.extension = easeOutQuart(progress);
          
          // Move tip along grab direction
          const targetDist = tentacle.naturalLength * tentacle.extension;
          tentacle.tipX = tentacle.anchorX + tentacle.grabDirectionX * targetDist;
          tentacle.tipY = tentacle.anchorY + tentacle.grabDirectionY * targetDist;
          
          if (progress >= 1) {
            // Fully extended — check if cursor is close enough to attach
            const distToTip = distance(state.cursorX, state.cursorY, tentacle.tipX, tentacle.tipY);
            
            if (distToTip < config.ATTACH_RADIUS && state.cursorInZone) {
              // ATTACH: soft-lock to cursor
              tentacle.state = 'attached';
              tentacle.tipTargetX = state.cursorX;
              tentacle.tipTargetY = state.cursorY;
            } else if (!state.cursorInZone) {
              // Cursor left — release
              tentacle.state = 'releasing';
              tentacle.stateStartTime = timestamp;
              tentacle.releaseTipStartX = tentacle.tipX;
              tentacle.releaseTipStartY = tentacle.tipY;
            } else {
              // Cursor too far to attach — release
              tentacle.state = 'releasing';
              tentacle.stateStartTime = timestamp;
              tentacle.releaseTipStartX = tentacle.tipX;
              tentacle.releaseTipStartY = tentacle.tipY;
            }
          }
          break;
        }

        // ─────────────────────────────────────────────────────────────────
        // ATTACHED: Tip follows cursor with resistance (no timer!)
        // ─────────────────────────────────────────────────────────────────
        case 'attached': {
          tentacle.extension = 1;
          
          // Update tip target to cursor position
          tentacle.tipTargetX = state.cursorX;
          tentacle.tipTargetY = state.cursorY;
          
          // Damped spring physics for tip movement
          const dx = tentacle.tipTargetX - tentacle.tipX;
          const dy = tentacle.tipTargetY - tentacle.tipY;
          
          // Spring force
          tentacle.tipVelX += dx * config.TIP_STIFFNESS;
          tentacle.tipVelY += dy * config.TIP_STIFFNESS;
          
          // Damping
          tentacle.tipVelX *= config.TIP_DAMPING;
          tentacle.tipVelY *= config.TIP_DAMPING;
          
          // Apply velocity
          tentacle.tipX += tentacle.tipVelX;
          tentacle.tipY += tentacle.tipVelY;
          
          // Calculate current stretch
          const currentDist = distance(tentacle.anchorX, tentacle.anchorY, tentacle.tipX, tentacle.tipY);
          const maxLength = tentacle.naturalLength * (1 + config.MAX_STRETCH_FACTOR);
          
          if (currentDist > tentacle.naturalLength) {
            tentacle.stretchAmount = (currentDist - tentacle.naturalLength) / 
                                     (maxLength - tentacle.naturalLength);
            
            if (tentacle.stretchAmount > 0.3) {
              tentacle.state = 'stretched';
            }
          } else {
            tentacle.stretchAmount = 0;
          }
          
          // Check for cursor exiting zone (handled in checkProximity)
          break;
        }

        // ─────────────────────────────────────────────────────────────────
        // STRETCHED: Near max stretch, about to release
        // ─────────────────────────────────────────────────────────────────
        case 'stretched': {
          tentacle.extension = 1;
          
          // Same physics as attached
          tentacle.tipTargetX = state.cursorX;
          tentacle.tipTargetY = state.cursorY;
          
          const dx = tentacle.tipTargetX - tentacle.tipX;
          const dy = tentacle.tipTargetY - tentacle.tipY;
          
          tentacle.tipVelX += dx * config.TIP_STIFFNESS;
          tentacle.tipVelY += dy * config.TIP_STIFFNESS;
          tentacle.tipVelX *= config.TIP_DAMPING;
          tentacle.tipVelY *= config.TIP_DAMPING;
          tentacle.tipX += tentacle.tipVelX;
          tentacle.tipY += tentacle.tipVelY;
          
          // Calculate stretch and constrain
          const currentDist = distance(tentacle.anchorX, tentacle.anchorY, tentacle.tipX, tentacle.tipY);
          const maxLength = tentacle.naturalLength * (1 + config.MAX_STRETCH_FACTOR);
          
          if (currentDist > maxLength) {
            // RELEASE: exceeded max stretch
            tentacle.state = 'releasing';
            tentacle.stateStartTime = timestamp;
            tentacle.releaseTipStartX = tentacle.tipX;
            tentacle.releaseTipStartY = tentacle.tipY;
          } else if (currentDist > tentacle.naturalLength) {
            tentacle.stretchAmount = (currentDist - tentacle.naturalLength) / 
                                     (maxLength - tentacle.naturalLength);
          } else {
            // Relaxed back to natural — return to attached
            tentacle.stretchAmount = 0;
            tentacle.state = 'attached';
          }
          break;
        }

        // ─────────────────────────────────────────────────────────────────
        // RELEASING: Smooth retraction back to anchor
        // ─────────────────────────────────────────────────────────────────
        case 'releasing': {
          const progress = Math.min(elapsed / config.RELEASE_DURATION, 1);
          const eased = easeInOutCubic(progress);
          
          tentacle.extension = 1 - eased;
          tentacle.stretchAmount = 0;
          
          // Interpolate tip back toward anchor from stored start position
          tentacle.tipX = tentacle.releaseTipStartX + (tentacle.anchorX - tentacle.releaseTipStartX) * eased;
          tentacle.tipY = tentacle.releaseTipStartY + (tentacle.anchorY - tentacle.releaseTipStartY) * eased;
          
          if (progress >= 1) {
            tentacle.state = 'dormant';
            tentacle.tipX = tentacle.anchorX;
            tentacle.tipY = tentacle.anchorY;
            tentacle.tipVelX = 0;
            tentacle.tipVelY = 0;
          }
          break;
        }
      }
    });
  }, []);

  return { getState, setBotPosition, checkProximity, tick };
}

// ═══════════════════════════════════════════════════════════════════════════
// GEOMETRY: Generate bezier curve points for rendering
// ═══════════════════════════════════════════════════════════════════════════

export function getTentacleCurve(
  tentacle: Tentacle,
  _botX: number,
  _botY: number,
  _botRadius: number
): { x: number; y: number }[] {
  const config = TENTACLE_CONFIG;
  
  if (tentacle.extension <= 0.01) {
    return [];
  }
  
  const points: { x: number; y: number }[] = [];
  const segments = config.SEGMENT_COUNT;
  
  // Start at anchor (behind bot)
  const startX = tentacle.anchorX;
  const startY = tentacle.anchorY;
  
  // End at current tip position
  const endX = tentacle.tipX;
  const endY = tentacle.tipY;
  
  // Control points for cubic bezier (creates organic curve)
  // First control: extends from anchor in grab direction
  const ctrl1Dist = tentacle.naturalLength * 0.3;
  const ctrl1X = startX + tentacle.grabDirectionX * ctrl1Dist;
  const ctrl1Y = startY + tentacle.grabDirectionY * ctrl1Dist;
  
  // Second control: pulls toward tip but with perpendicular offset
  const tipDist = distance(startX, startY, endX, endY);
  const perpX = -tentacle.grabDirectionY * 0.1 * tipDist;
  const perpY = tentacle.grabDirectionX * 0.1 * tipDist;
  const ctrl2X = endX - tentacle.grabDirectionX * ctrl1Dist + perpX;
  const ctrl2Y = endY - tentacle.grabDirectionY * ctrl1Dist + perpY;
  
  // Generate cubic bezier curve
  for (let i = 0; i <= segments; i++) {
    const t = i / segments;
    const t2 = t * t;
    const t3 = t2 * t;
    const mt = 1 - t;
    const mt2 = mt * mt;
    const mt3 = mt2 * mt;
    
    const x = mt3 * startX + 3 * mt2 * t * ctrl1X + 3 * mt * t2 * ctrl2X + t3 * endX;
    const y = mt3 * startY + 3 * mt2 * t * ctrl1Y + 3 * mt * t2 * ctrl2Y + t3 * endY;
    
    points.push({ x, y });
  }
  
  return points;
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORT TYPES
// ═══════════════════════════════════════════════════════════════════════════

export type { Tentacle, TentacleSystemState, TentacleState };
