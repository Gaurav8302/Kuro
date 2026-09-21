import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '@clerk/clerk-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useExperience } from '../ExperienceContext';
import { DUR, EASE, lineVariants, lineVariantsReduced } from '../motion';

/**
 * ORIGIN — the threshold.
 *
 *   KURO
 *   ◉ (Core, from the environment)
 *   An intelligence that remembers.
 *   ENTER KURO
 *
 * ENTER is not a route change. The Core comes forward, the environment
 * contracts, the words recede — then Identity emerges in the same place.
 *
 * Returning people are recognised and taken straight to chat.
 */
const Origin: React.FC = () => {
  const navigate = useNavigate();
  const { isLoaded, isSignedIn, user } = useUser();
  const { setStage, setCoreMode, reducedMotion, profile, isMobile } = useExperience();
  const [phase, setPhase] = useState<'origin' | 'entering' | 'recognising'>('origin');
  const timers = useRef<number[]>([]);

  useEffect(() => {
    setStage(phase === 'entering' ? 'entering' : 'origin');
    setCoreMode(phase === 'origin' ? 'idle' : 'attention');
  }, [phase, setStage, setCoreMode]);

  useEffect(() => () => timers.current.forEach((t) => window.clearTimeout(t)), []);

  // Recognition: a signed-in person is not asked to enter again.
  useEffect(() => {
    if (!isLoaded || !isSignedIn || phase !== 'origin') return;
    setPhase('recognising');
    const t = window.setTimeout(() => navigate('/chat', { replace: true }), reducedMotion ? 300 : 1250);
    timers.current.push(t);
  }, [isLoaded, isSignedIn, phase, navigate, reducedMotion]);

  const enter = useCallback(() => {
    if (phase !== 'origin') return;
    setPhase('entering');
    const t = window.setTimeout(() => navigate('/enter'), reducedMotion ? 120 : DUR.experience * 1000 * 0.95);
    timers.current.push(t);
  }, [phase, navigate, reducedMotion]);

  const lv = reducedMotion ? lineVariantsReduced : lineVariants;
  const displayName = profile.name || user?.firstName || null;
  const coreHalf = (isMobile ? 264 * 0.74 : 264) / 2;

  return (
    <div className="relative h-full w-full">
      {/* Identity — above the Core */}
      <AnimatePresence>
        {phase !== 'entering' && (
          <motion.div
            key="mark"
            className="absolute inset-x-0 top-[50%] mx-auto text-center"
            style={{ marginTop: -(coreHalf + 64) }}
            variants={lv}
            initial="hidden"
            animate="show"
            exit="exit"
            custom={0}
          >
            <span className="k-label !text-[0.8125rem] !tracking-[0.5em] !text-foreground/85">KURO</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Statement + action — below the Core */}
      <div
        className="absolute left-1/2 top-[50%] flex w-[min(92vw,640px)] -translate-x-1/2 flex-col items-center text-center"
        style={{ marginTop: coreHalf + 36 }}
      >
        <AnimatePresence mode="wait">
          {phase === 'recognising' ? (
            <motion.div
              key="recognise"
              className="flex flex-col items-center gap-5"
              variants={lv}
              initial="hidden"
              animate="show"
              exit="exit"
            >
              <p className="k-voice text-[clamp(1.375rem,3.2vw,2rem)]">
                {displayName ? (
                  <>
                    Welcome back, <span className="font-normal">{displayName}</span>.
                  </>
                ) : (
                  'Welcome back.'
                )}
              </p>
              <span className="k-label">Restoring context</span>
            </motion.div>
          ) : phase === 'origin' ? (
            <motion.div key="statement" className="flex flex-col items-center gap-9" exit="exit" variants={lv}>
              <motion.p
                className="k-voice text-[clamp(1.375rem,3.2vw,2.125rem)]"
                variants={lv}
                initial="hidden"
                animate="show"
                custom={1}
              >
                An intelligence that remembers.
              </motion.p>
              <motion.div variants={lv} initial="hidden" animate="show" custom={2}>
                <button type="button" onClick={enter} className="k-action">
                  Enter Kuro
                </button>
              </motion.div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      {/* Bottom-right: quiet meta */}
      <AnimatePresence>
        {phase === 'origin' && (
          <motion.div
            key="meta"
            className="absolute bottom-7 right-7 hidden md:block"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { delay: 0.5, duration: DUR.interface, ease: EASE.out } }}
            exit={{ opacity: 0, transition: { duration: DUR.interface * 0.6 } }}
          >
            <span className="k-label !text-muted-foreground/50">Memory · Context · Presence</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Origin;
