import React, { memo, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useExperience } from './ExperienceContext';
import { KuroCore, CORE_BASE } from './KuroCore';
import { CORE_ANCHORS, CHAT_CORE_OFFSET } from './types';
import { DUR, EASE } from './motion';

/**
 * KuroEnvironment — the part of Kuro that never unmounts.
 *
 *   • Background: two quiet light layers that crossfade with the stage.
 *   • Core: one canvas, repositioned by transform between stage anchors.
 *
 * Nothing here is decorative for its own sake: the light follows the Core,
 * the Core follows the stage, and the stage follows the person.
 */

function useViewport() {
  const [vp, setVp] = useState(() => ({
    w: typeof window !== 'undefined' ? window.innerWidth : 1280,
    h: typeof window !== 'undefined' ? window.innerHeight : 800,
  }));
  useEffect(() => {
    let raf = 0;
    const onResize = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setVp({ w: window.innerWidth, h: window.innerHeight }));
    };
    window.addEventListener('resize', onResize);
    window.addEventListener('orientationchange', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('orientationchange', onResize);
      cancelAnimationFrame(raf);
    };
  }, []);
  return vp;
}

export const KuroEnvironment = memo(function KuroEnvironment() {
  const { stage, coreMode, memoryNodes, pointer, reducedMotion, isMobile } = useExperience();
  const vp = useViewport();

  const anchor = CORE_ANCHORS[stage];
  const isChat = stage === 'chat';
  const mobileFactor = isMobile && !isChat ? 0.74 : 1;
  const size = Math.round(anchor.size * mobileFactor);

  const cx = isChat ? CHAT_CORE_OFFSET.x : anchor.x * vp.w;
  const cy = isChat ? CHAT_CORE_OFFSET.y : anchor.y * vp.h;
  const x = cx - CORE_BASE / 2;
  const y = cy - CORE_BASE / 2;
  const scale = size / CORE_BASE;

  const interactive = stage === 'origin' || stage === 'identity' || stage === 'awakening' || stage === 'onboarding';

  const moveTransition = reducedMotion
    ? { duration: 0 }
    : { duration: stage === 'entering' ? DUR.experience : DUR.experience + 0.2, ease: EASE.settle };

  // Which light is on.
  const lightCentre = stage === 'origin' || stage === 'entering' || stage === 'awakening' || stage === 'genesis' || stage === 'connecting' || stage === 'lost' ? 1 : 0;
  const lightUpper = stage === 'identity' || stage === 'onboarding' ? 1 : 0;
  const lightFlat = isChat ? 1 : 0;
  const contract = stage === 'entering' ? 1 : 0;

  const fade = reducedMotion ? { duration: 0 } : { duration: DUR.experience, ease: EASE.inOut };

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden="true">
      {/* Base */}
      <div className="absolute inset-0 bg-background" />

      {/* Light: centre (Origin / Awakening / Genesis) */}
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 60% 55% at 50% 50%, hsl(var(--primary) / 0.07) 0%, hsl(var(--primary) / 0.02) 40%, transparent 70%)',
        }}
        initial={false}
        animate={{ opacity: lightCentre }}
        transition={fade}
      />

      {/* Light: upper (Identity / Onboarding) */}
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 70% 50% at 50% 28%, hsl(var(--primary) / 0.06) 0%, hsl(var(--primary) / 0.015) 45%, transparent 72%)',
        }}
        initial={false}
        animate={{ opacity: lightUpper }}
        transition={fade}
      />

      {/* Light: flat (Chat) — barely there, keeps the top from being a hard edge */}
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(180deg, hsl(var(--primary) / 0.035) 0%, transparent 22%)',
        }}
        initial={false}
        animate={{ opacity: lightFlat }}
        transition={fade}
      />

      {/* Contraction: the environment closes in while entering */}
      <motion.div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 48% 44% at 50% 50%, transparent 40%, hsl(var(--background)) 100%)',
        }}
        initial={false}
        animate={{ opacity: contract }}
        transition={reducedMotion ? { duration: 0 } : { duration: DUR.experience * 0.9, ease: EASE.inOut }}
      />

      {/* The Core */}
      <motion.div
        className="absolute left-0 top-0 will-change-transform"
        style={{ width: CORE_BASE, height: CORE_BASE, transformOrigin: '50% 50%' }}
        initial={false}
        animate={{ x, y, scale }}
        transition={moveTransition}
      >
        <KuroCore
          mode={coreMode}
          nodes={memoryNodes}
          targetSize={size}
          pointer={pointer}
          interactive={interactive && !isMobile}
          reducedMotion={reducedMotion}
        />
      </motion.div>
    </div>
  );
});

export default KuroEnvironment;
