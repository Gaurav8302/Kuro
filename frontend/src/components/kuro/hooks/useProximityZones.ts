/**
 * Proximity Zone Detection
 * 
 * Calculates distance between firefly and bot, determines current zone,
 * and manages state machine transitions.
 * 
 * All calculations in refs - zero React re-renders.
 */

import { useRef, useCallback, useEffect } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
// TUNING CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

export const PROXIMITY_CONFIG = {
  // Zone radii (pixels from bot center) - REDUCED for shorter tentacles
  AWARENESS_RADIUS: 200,       // Bot notices firefly
  INTEREST_RADIUS: 140,        // Bot shows interest, limbs begin emerging
  ATTACK_RADIUS: 70,           // Bot attempts catch
  CATCH_RADIUS: 25,            // Actual catch hitbox (rare, intentionally small)
  
  // Timing
  ZONE_DEBOUNCE_MS: 100,       // Prevent rapid zone flickering
  ATTACK_COOLDOWN_MS: 800,     // Minimum time between attack attempts
  CATCH_WINDOW_MS: 150,        // How long catch hitbox is active during lunge
  
  // Prediction
  VELOCITY_PREDICTION_FRAMES: 8, // How many frames ahead to predict firefly position
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

export type ProximityZone = 'idle' | 'aware' | 'interested' | 'attacking' | 'reset';

export interface ProximityState {
  zone: ProximityZone;
  distance: number;
  angle: number;                    // Angle from bot to firefly (radians)
  predictedX: number;               // Where firefly will be
  predictedY: number;
  intensity: number;                // 0-1, how deep into current zone
  lastAttackTime: number;
  catchAttemptActive: boolean;
}

export interface BotPosition {
  x: number;
  y: number;
  radius: number;                   // Bot's visual radius for calculations
}

export interface ProximityControls {
  getState: () => ProximityState;
  setBotPosition: (pos: BotPosition) => void;
  update: (fireflyX: number, fireflyY: number, fireflyVx: number, fireflyVy: number) => ProximityZone;
  attemptCatch: () => boolean;      // Returns true if catch successful
}

// ═══════════════════════════════════════════════════════════════════════════
// STATE MACHINE TRANSITIONS
// ═══════════════════════════════════════════════════════════════════════════

const ZONE_TRANSITIONS: Record<ProximityZone, ProximityZone[]> = {
  idle: ['aware'],
  aware: ['idle', 'interested'],
  interested: ['aware', 'attacking'],
  attacking: ['interested', 'reset'],
  reset: ['idle', 'aware'],
};

function canTransition(from: ProximityZone, to: ProximityZone): boolean {
  return ZONE_TRANSITIONS[from]?.includes(to) ?? false;
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN HOOK
// ═══════════════════════════════════════════════════════════════════════════

export function useProximityZones(): ProximityControls {
  const stateRef = useRef<ProximityState>({
    zone: 'idle',
    distance: Infinity,
    angle: 0,
    predictedX: 0,
    predictedY: 0,
    intensity: 0,
    lastAttackTime: 0,
    catchAttemptActive: false,
  });

  const botRef = useRef<BotPosition>({
    x: 0,
    y: 0,
    radius: 100,
  });

  const lastZoneChangeRef = useRef(0);
  const resetTimeoutRef = useRef<number | null>(null);

  // Cleanup
  useEffect(() => {
    return () => {
      if (resetTimeoutRef.current) {
        clearTimeout(resetTimeoutRef.current);
      }
    };
  }, []);

  const getState = useCallback((): ProximityState => {
    return stateRef.current;
  }, []);

  const setBotPosition = useCallback((pos: BotPosition) => {
    botRef.current = pos;
  }, []);

  const update = useCallback((
    fireflyX: number,
    fireflyY: number,
    fireflyVx: number,
    fireflyVy: number
  ): ProximityZone => {
    const state = stateRef.current;
    const bot = botRef.current;
    const config = PROXIMITY_CONFIG;
    const now = performance.now();

    // ─────────────────────────────────────────────────────────────────────
    // DISTANCE CALCULATION
    // ─────────────────────────────────────────────────────────────────────
    
    const dx = fireflyX - bot.x;
    const dy = fireflyY - bot.y;
    state.distance = Math.sqrt(dx * dx + dy * dy);
    state.angle = Math.atan2(dy, dx);

    // ─────────────────────────────────────────────────────────────────────
    // VELOCITY PREDICTION (where firefly will be)
    // ─────────────────────────────────────────────────────────────────────
    
    state.predictedX = fireflyX + fireflyVx * config.VELOCITY_PREDICTION_FRAMES;
    state.predictedY = fireflyY + fireflyVy * config.VELOCITY_PREDICTION_FRAMES;

    // ─────────────────────────────────────────────────────────────────────
    // ZONE DETERMINATION
    // ─────────────────────────────────────────────────────────────────────
    
    let targetZone: ProximityZone = 'idle';
    
    if (state.distance < config.ATTACK_RADIUS) {
      targetZone = 'attacking';
      // Calculate intensity (how close to center of zone)
      state.intensity = 1 - (state.distance / config.ATTACK_RADIUS);
    } else if (state.distance < config.INTEREST_RADIUS) {
      targetZone = 'interested';
      state.intensity = 1 - ((state.distance - config.ATTACK_RADIUS) / 
        (config.INTEREST_RADIUS - config.ATTACK_RADIUS));
    } else if (state.distance < config.AWARENESS_RADIUS) {
      targetZone = 'aware';
      state.intensity = 1 - ((state.distance - config.INTEREST_RADIUS) / 
        (config.AWARENESS_RADIUS - config.INTEREST_RADIUS));
    } else {
      state.intensity = 0;
    }

    // ─────────────────────────────────────────────────────────────────────
    // STATE MACHINE TRANSITIONS (with debounce)
    // ─────────────────────────────────────────────────────────────────────
    
    // Don't transition during reset
    if (state.zone === 'reset') {
      return state.zone;
    }

    // Debounce rapid changes
    if (now - lastZoneChangeRef.current < config.ZONE_DEBOUNCE_MS) {
      return state.zone;
    }

    // Check valid transition
    if (targetZone !== state.zone) {
      // Special case: can always go to reset after attacking
      if (state.zone === 'attacking' && targetZone !== 'attacking') {
        state.zone = 'reset';
        lastZoneChangeRef.current = now;
        
        // Auto-exit reset after brief period
        resetTimeoutRef.current = window.setTimeout(() => {
          if (stateRef.current.zone === 'reset') {
            stateRef.current.zone = 'idle';
          }
        }, 400);
        
        return state.zone;
      }

      // Normal transitions
      if (canTransition(state.zone, targetZone)) {
        state.zone = targetZone;
        lastZoneChangeRef.current = now;
      } else {
        // Try intermediate state
        const intermediates = ZONE_TRANSITIONS[state.zone];
        for (const intermediate of intermediates) {
          if (canTransition(intermediate, targetZone)) {
            state.zone = intermediate;
            lastZoneChangeRef.current = now;
            break;
          }
        }
      }
    }

    return state.zone;
  }, []);

  const attemptCatch = useCallback((): boolean => {
    const state = stateRef.current;
    const config = PROXIMITY_CONFIG;
    const now = performance.now();

    // Check cooldown
    if (now - state.lastAttackTime < config.ATTACK_COOLDOWN_MS) {
      return false;
    }

    // Check if in catch range
    if (state.distance < config.CATCH_RADIUS) {
      state.lastAttackTime = now;
      state.catchAttemptActive = true;
      
      // Catch window
      setTimeout(() => {
        stateRef.current.catchAttemptActive = false;
      }, config.CATCH_WINDOW_MS);
      
      // Rare catch - only 15% chance even when in range
      return Math.random() < 0.15;
    }

    state.lastAttackTime = now;
    return false;
  }, []);

  return { getState, setBotPosition, update, attemptCatch };
}
