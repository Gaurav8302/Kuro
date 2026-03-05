/**
 * ProximityController v2 — Simplified Orchestrator
 * 
 * Coordinates:
 * - Firefly cursor (follows mouse with physics)
 * - Tentacles (reactive, edge-triggered, non-tracking)
 * - Bot glow/behavior responses
 * 
 * Key changes from v1:
 * - Tentacles are now edge-triggered, not continuous
 * - No complex zone state machine for limbs
 * - Tentacles manage their own state internally
 */

import { useRef, useEffect, useCallback, useState } from 'react';
import FireflyCursor, { type FireflyCursorHandle } from './FireflyCursor';
import Tentacles, { type TentaclesHandle } from './Tentacles';
import { TENTACLE_CONFIG } from './hooks/useTentacleSystem';
import { FIREFLY_CONFIG } from './hooks/useFireflyPhysics';

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

type ProximityZone = 'idle' | 'near' | 'close';

interface ProximityControllerProps {
  enabled?: boolean;
  botContainerRef: React.RefObject<HTMLDivElement>;
  onZoneChange?: (zone: ProximityZone) => void;
  onCatch?: () => void;
}

export interface BotBehaviorState {
  zone: ProximityZone;
  glowIntensity: number;
}

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export default function ProximityController({
  enabled = true,
  botContainerRef,
  onZoneChange,
  onCatch,
}: ProximityControllerProps) {
  // Component refs
  const fireflyRef = useRef<FireflyCursorHandle>(null);
  const tentaclesRef = useRef<TentaclesHandle>(null);
  
  // Animation frame ref
  const frameRef = useRef<number>(0);
  
  // Bot position cache
  const botPosRef = useRef({ x: 0, y: 0, radius: 100 });
  
  // Track zone for bot glow
  const lastZoneRef = useRef<ProximityZone>('idle');

  // State for bot behavior (minimal updates)
  const [botBehavior, setBotBehavior] = useState<BotBehaviorState>({
    zone: 'idle',
    glowIntensity: 1,
  });

  // ─────────────────────────────────────────────────────────────────────────
  // BOT POSITION TRACKING
  // ─────────────────────────────────────────────────────────────────────────

  const updateBotPosition = useCallback(() => {
    if (!botContainerRef.current) return;

    const rect = botContainerRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const radius = Math.min(rect.width, rect.height) / 2;

    botPosRef.current = { x: centerX, y: centerY, radius };
    tentaclesRef.current?.setBotPosition(centerX, centerY, radius);
  }, [botContainerRef]);

  // ─────────────────────────────────────────────────────────────────────────
  // MAIN LOOP
  // ─────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!enabled) return;

    let isActive = true;

    const tick = () => {
      if (!isActive) return;

      // Update bot position
      updateBotPosition();

      // Get firefly state
      const fireflyState = fireflyRef.current?.getState();
      if (!fireflyState) {
        frameRef.current = requestAnimationFrame(tick);
        return;
      }

      // Pass cursor position to tentacles for edge detection
      tentaclesRef.current?.checkProximity(fireflyState.x, fireflyState.y);

      // ─────────────────────────────────────────────────────────────────────
      // SIMPLE ZONE DETECTION (for bot glow only)
      // ─────────────────────────────────────────────────────────────────────

      const dx = fireflyState.x - botPosRef.current.x;
      const dy = fireflyState.y - botPosRef.current.y;
      const distance = Math.sqrt(dx * dx + dy * dy);

      let zone: ProximityZone = 'idle';
      if (distance < TENTACLE_CONFIG.ACTIVATION_RADIUS * 0.6) {
        zone = 'close';
      } else if (distance < TENTACLE_CONFIG.ACTIVATION_RADIUS) {
        zone = 'near';
      }

      // Update bot glow on zone change
      if (zone !== lastZoneRef.current) {
        lastZoneRef.current = zone;
        onZoneChange?.(zone);
        
        setBotBehavior({
          zone,
          glowIntensity: zone === 'close' ? 1.4 : zone === 'near' ? 1.2 : 1,
        });
      }

      // ─────────────────────────────────────────────────────────────────────
      // RARE CATCH LOGIC (optional, very rare)
      // ─────────────────────────────────────────────────────────────────────

      const catchRadius = 30;
      if (distance < catchRadius && !fireflyState.isCaught && Math.random() < 0.002) {
        // Very rare catch
        fireflyRef.current?.triggerCatch(botPosRef.current.x, botPosRef.current.y);
        onCatch?.();

        setTimeout(() => {
          const respawnX = botPosRef.current.x + (Math.random() - 0.5) * 200;
          const respawnY = botPosRef.current.y - 150;
          fireflyRef.current?.respawn(respawnX, respawnY);
        }, FIREFLY_CONFIG.RESPAWN_DELAY);
      }

      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);

    window.addEventListener('resize', updateBotPosition, { passive: true });
    window.addEventListener('scroll', updateBotPosition, { passive: true });

    return () => {
      isActive = false;
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener('resize', updateBotPosition);
      window.removeEventListener('scroll', updateBotPosition);
    };
  }, [enabled, updateBotPosition, onZoneChange, onCatch]);

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────

  if (!enabled) return null;

  return (
    <>
      {/* Tentacles render BEHIND bot (z-index 90) */}
      <Tentacles ref={tentaclesRef} enabled={enabled} />
      
      {/* Firefly cursor on top (z-index 9999) */}
      <FireflyCursor ref={fireflyRef} enabled={enabled} />
    </>
  );
}

export { TENTACLE_CONFIG };
