import { useState, useEffect, memo, lazy, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { KuroBackground } from './KuroBackground';

const KuroBot3D = lazy(() => import('./KuroBot3D'));

interface KuroIntroProps {
  phrases?: string[];
  cycleMs?: number;
  fullscreen?: boolean;
  className?: string;
  onFinish?: () => void;
  userName?: string;
}

/**
 * KuroIntro - Professional welcome animation
 * Shows Kuro avatar with animated text phrases
 */
export const KuroIntro = memo(function KuroIntro({
  phrases = ['Welcome', "Let's Create", "Let's Build", 'Kuro AI'],
  cycleMs = 1600,
  fullscreen = true,
  className = '',
  onFinish,
  userName,
}: KuroIntroProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Customize first phrase if userName provided
  const displayPhrases = userName 
    ? [`Welcome, ${userName}`, ...phrases.slice(1)]
    : phrases;

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentIndex((prev) => {
        const next = (prev + 1) % displayPhrases.length;
        // Call onFinish after last phrase completes one cycle
        if (next === 0 && prev === displayPhrases.length - 1 && onFinish) {
          setTimeout(onFinish, 500);
        }
        return next;
      });
    }, cycleMs);

    return () => clearInterval(interval);
  }, [displayPhrases.length, cycleMs, onFinish]);

  const currentPhrase = displayPhrases[currentIndex];

  return (
    <div
      className={`
        ${fullscreen ? 'fixed inset-0 z-[9999]' : 'relative w-full h-96 rounded-2xl overflow-hidden'}
        flex items-center justify-center
        bg-background
        ${className}
      `}
    >
      <KuroBackground variant="hero" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center px-6">
        {/* 3D Kuro Bot with head cursor following */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0, 0, 0.2, 1] }}
            className={`mb-8 shrink-0 ${fullscreen ? 'min-h-[14rem] md:min-h-[18rem]' : 'min-h-[9rem] md:min-h-[11rem]'}`}
          >
            <Suspense fallback={
              <div className={`${fullscreen ? 'h-56 w-56 md:h-72 md:w-72' : 'h-36 w-36 md:h-44 md:w-44'} flex items-center justify-center`}>
                <div className="w-12 h-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin" />
              </div>
            }>
              <KuroBot3D className={fullscreen ? 'h-56 w-56 md:h-72 md:w-72' : 'h-36 w-36 md:h-44 md:w-44'} />
            </Suspense>
          </motion.div>

          {/* Animated phrase */}
          <div className="h-20 md:h-24 relative flex items-center justify-center overflow-hidden">
            <AnimatePresence mode="wait">
            <motion.h1
              key={currentPhrase}
              className={`
                font-bold tracking-tight text-foreground
                ${fullscreen ? 'text-4xl md:text-6xl' : 'text-3xl md:text-4xl'}
              `}
              initial={{ opacity: 0, y: 20, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -20, filter: 'blur(8px)' }}
              transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
            >
              {currentPhrase}
            </motion.h1>
          </AnimatePresence>
        </div>

        {/* Accent line */}
        <motion.div
          className="w-32 h-1 rounded-full mt-4 kuro-gradient"
          initial={{ scaleX: 0, opacity: 0 }}
          animate={{ scaleX: 1, opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        />

        {/* Subtitle */}
        {fullscreen && (
          <motion.p
            className="mt-8 text-muted-foreground text-sm md:text-base max-w-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.5 }}
          >
            Your intelligent AI assistant for creative problem solving
          </motion.p>
        )}
      </div>
    </div>
  );
});

export default KuroIntro;
