import React, { memo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useExperience } from './ExperienceContext';
import { JOURNEY, STAGE_LABEL } from './types';
import { DUR, EASE } from './motion';
import { cn } from '@/lib/utils';

const DESCRIPTOR: Record<string, string> = {
  ORIGIN: 'The threshold. An intelligence that remembers.',
  IDENTITY: 'Kuro needs to know who is speaking.',
  AWAKENING: 'The system becomes aware of you.',
  MEMORY: 'Context takes shape.',
  KURO: '',
  UNMAPPED: 'This place does not exist.',
};

/**
 * KuroRail — orientation, not navigation.
 *
 * A fixed left rail shows where in the journey you are. It fades out in chat,
 * where the person is working and the journey is complete.
 */
export const KuroRail = memo(function KuroRail() {
  const { stage, reducedMotion, isMobile, navOpen, setNavOpen } = useExperience();
  const label = STAGE_LABEL[stage];
  const isChat = stage === 'chat';
  const currentIndex = JOURNEY.findIndex((j) => j.stages.includes(stage));

  const t = reducedMotion ? { duration: 0 } : { duration: DUR.interface, ease: EASE.out };

  return (
    <>
      {/* Wordmark — always present, top-left. In chat the Core sits beside it. */}
      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-30 flex h-[60px] items-center"
        initial={false}
        animate={{ x: isChat ? 60 : 28 }}
        transition={reducedMotion ? { duration: 0 } : { duration: DUR.experience, ease: EASE.settle }}
      >
        <span className="k-label !tracking-[0.34em] !text-foreground/90">KURO</span>
      </motion.div>

      {/* Chat: the Core is the way into the system. A labelled control sits
          beside it so navigation is discoverable, not hidden. */}
      <AnimatePresence>
        {isChat && (
          <motion.div
            key="chat-nav"
            className="fixed left-0 top-0 z-30 flex h-[60px] items-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={t}
          >
            <button
              type="button"
              onClick={() => setNavOpen(!navOpen)}
              className="absolute left-[18px] top-[8px] h-11 w-11 rounded-full outline-none focus-visible:ring-1 focus-visible:ring-primary/60"
              aria-label={navOpen ? 'Close Kuro navigation' : 'Open Kuro navigation'}
              aria-expanded={navOpen}
            />
            <button
              type="button"
              onClick={() => setNavOpen(!navOpen)}
              className="k-quiet ml-[124px]"
              aria-expanded={navOpen}
            >
              {navOpen ? 'Close' : 'Menu'}
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Rail: stage label + journey (desktop, non-chat) */}
      <AnimatePresence>
        {!isChat && !isMobile && (
          <motion.aside
            key="rail"
            className="pointer-events-none fixed left-7 top-1/2 z-30 select-none"
            initial={{ opacity: 0, x: -6, y: '-50%' }}
            animate={{ opacity: 1, x: 0, y: '-50%' }}
            exit={{ opacity: 0, x: -6, y: '-50%' }}
            transition={t}
          >
            <div className="flex gap-5">
              <div className="relative w-px self-stretch k-hairline">
                <motion.div
                  className="absolute left-0 top-0 w-px bg-primary/80"
                  initial={false}
                  animate={{
                    height: `${((Math.max(0, currentIndex) + 1) / JOURNEY.length) * 100}%`,
                  }}
                  transition={reducedMotion ? { duration: 0 } : { duration: DUR.experience, ease: EASE.settle }}
                />
              </div>

              <div className="flex flex-col gap-6">
                <div className="min-h-[52px]">
                  <AnimatePresence mode="wait" initial={false}>
                    <motion.div
                      key={label}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      transition={t}
                    >
                      <div className="k-label !text-foreground">[ {label} ]</div>
                      <div className="k-label mt-2 max-w-[168px] !normal-case !tracking-[0.02em] leading-[1.5] !text-muted-foreground/80">
                        {DESCRIPTOR[label]}
                      </div>
                    </motion.div>
                  </AnimatePresence>
                </div>

                <ol className="flex flex-col gap-3">
                  {JOURNEY.map((j, i) => {
                    const active = i === currentIndex;
                    const passed = i < currentIndex;
                    return (
                      <li
                        key={j.id}
                        className={cn(
                          'k-label transition-colors [transition-duration:450ms]',
                          active && '!text-foreground',
                          passed && '!text-muted-foreground/70',
                          !active && !passed && '!text-muted-foreground/35'
                        )}
                      >
                        <span className="inline-block w-4 text-[9px]">{active ? '●' : passed ? '○' : ''}</span>
                        {j.label}
                      </li>
                    );
                  })}
                </ol>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Mobile: a single stage marker under the wordmark */}
      <AnimatePresence>
        {!isChat && isMobile && (
          <motion.div
            key="mobile-label"
            className="pointer-events-none fixed left-7 top-[58px] z-30"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={t}
          >
            <span className="k-label">[ {label} ]</span>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
});

export default KuroRail;
