/**
 * Limb/Tendril Kinematics
 * 
 * Creates organic energy tendrils that emerge from the bot when in 
 * interest/attack zones. Uses simplified inverse kinematics with
 * delay-based chain physics.
 * 
 * NOT humanoid. NOT cartoonish. Abstract energy appendages.
 */

import { useRef, useCallback } from 'react';

// ═══════════════════════════════════════════════════════════════════════════
// TUNING CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

export const LIMB_CONFIG = {
  // Structure
  NUM_LIMBS: 2,                     // Two tendrils - left and right
  SEGMENTS_PER_LIMB: 5,             // Fewer segments for shorter tentacles
  BASE_LENGTH: 25,                  // Length of each segment (pixels)
  
  // Emergence
  EMERGE_SPEED: 0.06,               // How fast limbs extend (0-1 per frame)
  RETRACT_SPEED: 0.04,              // How fast limbs retract
  
  // Physics
  CHAIN_DELAY: 0.12,                // Delay between segments (0-1)
  STIFFNESS: 0.15,                  // How quickly segments follow target
  DAMPING: 0.85,                    // Friction on segment movement
  
  // Targeting
  REACH_OVERSHOOT: 1.0,             // Don't overshoot
  ANTICIPATION_FACTOR: 0.8,         // Reduced anticipation
  
  // Visual
  BASE_THICKNESS: 10,               // Thicker at base
  TIP_THICKNESS: 6,                 // Round tip thickness
  GLOW_INTENSITY: 0.7,              // Base glow amount
  
  // Attack behavior
  LUNGE_SPEED: 0.2,                 // Speed multiplier during attack
  RETRACT_DELAY_MS: 300,            // Pause before retracting after miss
  
  // Anchor offset (behind the bot)
  ANCHOR_OFFSET_X: -60,             // How far behind the bot center
  ANCHOR_OFFSET_Y: 40,              // Vertical spread (left/right)
} as const;

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

export interface LimbSegment {
  x: number;
  y: number;
  vx: number;
  vy: number;
  angle: number;
  targetX: number;
  targetY: number;
}

export interface Limb {
  segments: LimbSegment[];
  baseAngle: number;                // Angle from bot center where limb originates
  extension: number;                // 0 = hidden, 1 = fully extended
  isLunging: boolean;
  retractTime: number;
}

export interface LimbState {
  limbs: Limb[];
  targetX: number;
  targetY: number;
  botX: number;
  botY: number;
  botRadius: number;
}

export interface LimbControls {
  getState: () => LimbState;
  setBotPosition: (x: number, y: number, radius: number) => void;
  setTarget: (x: number, y: number, vx: number, vy: number) => void;
  updateForZone: (zone: string, intensity: number) => void;
  triggerLunge: () => void;
  triggerRetract: () => void;
  tick: () => void;
}

// ═══════════════════════════════════════════════════════════════════════════
// HELPER: Initialize limbs
// ═══════════════════════════════════════════════════════════════════════════

function createLimbs(numLimbs: number, segmentsPerLimb: number): Limb[] {
  const limbs: Limb[] = [];
  
  for (let i = 0; i < numLimbs; i++) {
    // Two limbs emerging from BEHIND the bot
    // They start pointing backward, then curve around to reach forward
    const angle = i === 0 
      ? Math.PI * 0.85   // Left tentacle (pointing back-left)
      : -Math.PI * 0.85; // Right tentacle (pointing back-right)
    
    // Store which side this limb is on (0 = left, 1 = right)
    const side = i;
    
    const segments: LimbSegment[] = [];
    for (let j = 0; j < segmentsPerLimb; j++) {
      segments.push({
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
        angle: 0,
        targetX: 0,
        targetY: 0,
      });
    }
    
    limbs.push({
      segments,
      baseAngle: angle + Math.PI, // Point outward from bot
      extension: 0,
      isLunging: false,
      retractTime: 0,
    });
  }
  
  return limbs;
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN HOOK
// ═══════════════════════════════════════════════════════════════════════════

export function useLimbKinematics(): LimbControls {
  const stateRef = useRef<LimbState>({
    limbs: createLimbs(LIMB_CONFIG.NUM_LIMBS, LIMB_CONFIG.SEGMENTS_PER_LIMB),
    targetX: 0,
    targetY: 0,
    botX: 0,
    botY: 0,
    botRadius: 100,
  });

  const getState = useCallback((): LimbState => {
    return stateRef.current;
  }, []);

  const setBotPosition = useCallback((x: number, y: number, radius: number) => {
    stateRef.current.botX = x;
    stateRef.current.botY = y;
    stateRef.current.botRadius = radius;
  }, []);

  const setTarget = useCallback((x: number, y: number, vx: number, vy: number) => {
    const state = stateRef.current;
    // Apply anticipation - aim where target will be
    state.targetX = x + vx * LIMB_CONFIG.ANTICIPATION_FACTOR * 10;
    state.targetY = y + vy * LIMB_CONFIG.ANTICIPATION_FACTOR * 10;
  }, []);

  const updateForZone = useCallback((zone: string, intensity: number) => {
    const state = stateRef.current;
    const config = LIMB_CONFIG;
    const now = performance.now();
    
    state.limbs.forEach((limb) => {
      // Skip if in retract delay
      if (limb.retractTime > now) return;
      
      let targetExtension = 0;
      
      switch (zone) {
        case 'interested':
          // Partial emergence, scales with intensity
          targetExtension = 0.3 + intensity * 0.4;
          break;
        case 'attacking':
          // Full extension
          targetExtension = 1;
          break;
        case 'reset':
          // Begin retraction
          targetExtension = 0;
          break;
        default:
          targetExtension = 0;
      }
      
      // Smooth extension/retraction
      if (targetExtension > limb.extension) {
        limb.extension += config.EMERGE_SPEED;
        if (limb.extension > targetExtension) limb.extension = targetExtension;
      } else {
        limb.extension -= config.RETRACT_SPEED;
        if (limb.extension < 0) limb.extension = 0;
      }
    });
  }, []);

  const triggerLunge = useCallback(() => {
    stateRef.current.limbs.forEach(limb => {
      limb.isLunging = true;
    });
  }, []);

  const triggerRetract = useCallback(() => {
    const now = performance.now();
    stateRef.current.limbs.forEach(limb => {
      limb.isLunging = false;
      limb.retractTime = now + LIMB_CONFIG.RETRACT_DELAY_MS;
    });
  }, []);

  // ─────────────────────────────────────────────────────────────────────────
  // PHYSICS TICK (call every frame)
  // ─────────────────────────────────────────────────────────────────────────
  
  const tick = useCallback(() => {
    const state = stateRef.current;
    const config = LIMB_CONFIG;
    
    state.limbs.forEach((limb) => {
      if (limb.extension <= 0) {
        // Reset hidden limb positions
        limb.segments.forEach(seg => {
          seg.x = state.botX;
          seg.y = state.botY;
          seg.vx = 0;
          seg.vy = 0;
        });
        return;
      }
      
      const speedMultiplier = limb.isLunging ? config.LUNGE_SPEED : 1;
      
      // Determine side offset for this limb (left = -1, right = +1)
      const sideMultiplier = limb.baseAngle > 0 ? -1 : 1;
      
      // Process each segment
      limb.segments.forEach((segment, i) => {
        let targetX: number;
        let targetY: number;
        
        if (i === 0) {
          // First segment anchored BEHIND the bot
          // Use fixed offset from bot center (behind and to the side)
          targetX = state.botX + (config.ANCHOR_OFFSET_X ?? -60);
          targetY = state.botY + (config.ANCHOR_OFFSET_Y ?? 40) * sideMultiplier;
        } else {
          // Follow previous segment with delay
          const prev = limb.segments[i - 1];
          
          // Calculate direction toward final target
          const toTargetX = state.targetX - prev.x;
          const toTargetY = state.targetY - prev.y;
          const toTargetDist = Math.sqrt(toTargetX * toTargetX + toTargetY * toTargetY);
          
          // Limit max reach based on segment index
          const maxReach = config.BASE_LENGTH * config.SEGMENTS_PER_LIMB * 0.9;
          const distFromAnchor = Math.sqrt(
            Math.pow(prev.x - state.botX, 2) + 
            Math.pow(prev.y - state.botY, 2)
          );
          
          if (toTargetDist > 0 && distFromAnchor < maxReach) {
            // Normalized direction
            const dirX = toTargetX / toTargetDist;
            const dirY = toTargetY / toTargetDist;
            
            // Each segment extends toward target from previous segment
            const segmentLength = config.BASE_LENGTH * limb.extension;
            const reach = limb.isLunging ? config.REACH_OVERSHOOT : 1;
            
            targetX = prev.x + dirX * segmentLength * reach;
            targetY = prev.y + dirY * segmentLength * reach;
          } else {
            // At max reach, just follow previous segment direction
            const prevAngle = i > 1 
              ? Math.atan2(prev.y - limb.segments[i-2].y, prev.x - limb.segments[i-2].x)
              : limb.baseAngle;
            targetX = prev.x + Math.cos(prevAngle) * config.BASE_LENGTH * 0.5;
            targetY = prev.y + Math.sin(prevAngle) * config.BASE_LENGTH * 0.5;
          }
        }
        
        // Spring physics with chain delay
        const delay = 1 - (i * config.CHAIN_DELAY);
        const stiffness = config.STIFFNESS * delay * speedMultiplier;
        
        const dx = targetX - segment.x;
        const dy = targetY - segment.y;
        
        segment.vx += dx * stiffness;
        segment.vy += dy * stiffness;
        
        segment.vx *= config.DAMPING;
        segment.vy *= config.DAMPING;
        
        segment.x += segment.vx;
        segment.y += segment.vy;
        
        // Calculate angle for rendering
        if (i > 0) {
          const prev = limb.segments[i - 1];
          segment.angle = Math.atan2(segment.y - prev.y, segment.x - prev.x);
        } else {
          segment.angle = limb.baseAngle;
        }
      });
    });
  }, []);

  return { 
    getState, 
    setBotPosition, 
    setTarget, 
    updateForZone, 
    triggerLunge, 
    triggerRetract,
    tick 
  };
}
