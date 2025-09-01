import React, { useState, useEffect, useRef, useMemo, memo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useIsMobile } from '@/hooks/use-mobile';
import { useOptimizedAnimations } from '@/hooks/use-performance';

interface OptimizedKuroIntroProps {
  phrases?: string[];
  cycleMs?: number;
  fullscreen?: boolean;
  className?: string;
  onFinish?: () => void;
}

// Lightweight CSS-only intro for mobile
const LightweightIntro: React.FC<OptimizedKuroIntroProps> = memo(({ 
  phrases = ["Let's Imagine", "Let's Build", 'Kuro AI'], 
  cycleMs = 1800, 
  fullscreen = true, 
  className, 
  onFinish 
}) => {
  const [index, setIndex] = useState(0);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    const interval = setInterval(() => {
      setIndex(prev => {
        const next = (prev + 1) % phrases.length;
        if (onFinish && next === 0 && prev !== 0) {
          onFinish();
        }
        return next;
      });
    }, cycleMs);
    return () => {
      mounted.current = false;
      clearInterval(interval);
    };
  }, [phrases.length, cycleMs, onFinish]);

  const phrase = phrases[index];

  return (
    <div className={`
      ${fullscreen
        ? 'fixed inset-0 z-[9999]'
        : 'relative w-full h-[420px] md:h-[520px] rounded-3xl overflow-hidden'
      }
      overflow-hidden select-none bg-background/95 backdrop-blur-xl
      ${className || ''}
    `}>
      
      {/* Opaque holographic background */}
      <div className="absolute inset-0 bg-background/90" />
      <div className="absolute inset-0 bg-gradient-to-br from-holo-cyan-500/20 via-holo-purple-500/20 to-holo-blue-500/20" />
      
      {/* Static grid overlay */}
      <div 
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,230,214,0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,230,214,0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }}
      />

      {/* Center content with CSS animations only */}
      <div className="relative z-10 flex h-full w-full items-center justify-center p-6">
        <div className="flex flex-col items-center text-center">
          <div className="relative">
            <h1
              key={phrase}
              className={`
                font-bold tracking-wider holo-text text-holo-glow font-orbitron
                ${fullscreen ? 'text-4xl md:text-6xl' : 'text-3xl md:text-5xl'}
                animate-pulse
              `}
              style={{
                animation: 'holo-glow 2s ease-in-out infinite alternate'
              }}
            >
              {phrase}
            </h1>

            {/* Simple CSS underline */}
            <div className="mx-auto mt-6 h-1 w-40 rounded-full bg-gradient-to-r from-holo-cyan-500 via-holo-purple-400 to-holo-blue-500 shadow-holo-glow" />
          </div>

          {fullscreen && (
            <p className="mt-12 max-w-xl text-sm md:text-base text-holo-cyan-100/70 leading-relaxed font-space">
              Advanced neural interface for creators, innovators & quantum problem solvers.
            </p>
          )}
        </div>
      </div>

      {/* Simple CSS scan line */}
      <div 
        className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
        style={{
          animation: 'scan-line 4s linear infinite'
        }}
      />
    </div>
  );
});

// Full animated intro for desktop
const AnimatedIntro: React.FC<OptimizedKuroIntroProps> = memo(({ 
  phrases = ["Let's Imagine", "Let's Build", 'Kuro AI'], 
  cycleMs = 1800, 
  fullscreen = true, 
  className, 
  onFinish 
}) => {
  const [index, setIndex] = useState(0);
  const mounted = useRef(false);
  const { particleCount } = useOptimizedAnimations();

  // Pre-generate particles once
  const particles = useMemo(() => (
    Array.from({ length: particleCount }).map((_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: 2 + Math.random() * 6,
      delay: Math.random() * 8,
      duration: 8 + Math.random() * 12,
      opacity: 0.2 + Math.random() * 0.4
    }))
  ), [particleCount]);

  useEffect(() => {
    mounted.current = true;
    const interval = setInterval(() => {
      setIndex(prev => {
        const next = (prev + 1) % phrases.length;
        if (onFinish && next === 0 && prev !== 0) {
          onFinish();
        }
        return next;
      });
    }, cycleMs);
    return () => {
      mounted.current = false;
      clearInterval(interval);
    };
  }, [phrases.length, cycleMs, onFinish]);

  const phrase = phrases[index];

  return (
    <div className={`
      ${fullscreen
        ? 'fixed inset-0 z-[9999]'
        : 'relative w-full h-[420px] md:h-[520px] rounded-3xl overflow-hidden shadow-glow'
      }
      overflow-hidden select-none
      ${className || ''}
    `}>
      
      {/* Opaque holographic base background */}
      <div className="absolute inset-0 bg-background/90" />
      <div className="absolute inset-0 bg-gradient-to-br from-holo-cyan-900/30 to-holo-purple-900/30" />

      {/* Holographic radial glows */}
      <div className="absolute inset-0 mix-blend-screen opacity-70">
        <motion.div 
          className="absolute inset-0 bg-[radial-gradient(circle_at_30%_40%,rgba(0,230,214,0.4),transparent_60%)]"
          animate={{ scale: [1, 1.2, 1], opacity: [0.4, 0.7, 0.4] }}
          transition={{ duration: 4, repeat: Infinity }}
        />
        <motion.div 
          className="absolute inset-0 bg-[radial-gradient(circle_at_70%_60%,rgba(140,26,255,0.3),transparent_65%)]"
          animate={{ scale: [1.2, 1, 1.2], opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 5, repeat: Infinity }}
        />
        <motion.div 
          className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,rgba(26,140,255,0.25),transparent_70%)]"
          animate={{ scale: [1, 1.3, 1], opacity: [0.25, 0.5, 0.25] }}
          transition={{ duration: 6, repeat: Infinity }}
        />
      </div>

      {/* Holographic grid overlay */}
      <div className="pointer-events-none absolute inset-0 opacity-30" style={{
        background: `
          linear-gradient(rgba(0,230,214,0.1) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,230,214,0.1) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px'
      }} />

      {/* Particle layer */}
      <div className="absolute inset-0">
        {particles.map(p => (
          <motion.span
            key={p.id}
            className="absolute rounded-full blur-[1px]"
            style={{
              left: `${p.left}vw`,
              top: `${p.top}vh`,
              width: p.size,
              height: p.size,
              backgroundColor: ['#00e6d6', '#8c1aff', '#1a8cff', '#ff1ab1'][p.id % 4],
              boxShadow: `0 0 ${p.size * 2}px currentColor`
            }}
            animate={{
              y: [-20, -40, -20],
              x: [-10, 10, -10],
              scale: [1, 1.2, 1],
              opacity: [p.opacity, p.opacity * 1.5, p.opacity]
            }}
            transition={{
              duration: p.duration,
              repeat: Infinity,
              delay: p.delay,
              ease: 'easeInOut'
            }}
          />
        ))}
      </div>

      {/* Center content */}
      <div className="relative z-10 flex h-full w-full items-center justify-center p-6">
        <div className="flex flex-col items-center text-center">
          <div className="relative">
            <AnimatePresence mode="wait">
              <motion.h1
                key={phrase}
                initial={{ opacity: 0, scale: 0.8, y: 20, filter: 'blur(10px)' }}
                animate={{ 
                  opacity: 1, 
                  scale: 1, 
                  y: 0, 
                  filter: 'blur(0px)'
                }}
                exit={{ opacity: 0, scale: 0.9, y: -20, filter: 'blur(5px)' }}
                transition={{ 
                  duration: 0.8, 
                  ease: [0.25, 0.8, 0.25, 1]
                }}
                className={fullscreen
                  ? 'font-bold tracking-wider holo-text text-holo-glow text-6xl md:text-8xl font-orbitron'
                  : 'font-bold tracking-wider holo-text text-holo-glow text-5xl md:text-7xl font-orbitron'
                }
                style={{
                  textShadow: '0 0 20px #00e6d6, 0 0 40px #00e6d6'
                }}
              >
                {phrase}
              </motion.h1>
            </AnimatePresence>

            {/* Holographic underline */}
            <motion.div
              key={`underline-${phrase}`}
              initial={{ opacity: 0, scaleX: 0.2, filter: 'blur(5px)' }}
              animate={{ opacity: 1, scaleX: 1, filter: 'blur(0px)' }}
              exit={{ opacity: 0, scaleX: 0.3, filter: 'blur(3px)' }}
              transition={{ duration: 1, delay: 0.2 }}
              className="mx-auto mt-6 h-1 w-40 origin-center rounded-full bg-gradient-to-r from-holo-cyan-500 via-holo-purple-400 to-holo-blue-500 shadow-holo-glow"
            />
          </div>

          {fullscreen && (
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 0.8, y: 0 }}
              transition={{ delay: 0.6, duration: 1 }}
              className="mt-12 max-w-xl text-sm md:text-base text-holo-cyan-100/70 leading-relaxed font-space"
            >
              Advanced neural interface for creators, innovators & quantum problem solvers.
            </motion.p>
          )}
        </div>
      </div>

      {fullscreen && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-background via-background/60 to-transparent" />
      )}

      {/* Scan line effect */}
      <motion.div
        className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
        animate={{ y: ['0vh', '100vh'] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  );
});

export const OptimizedKuroIntro: React.FC<OptimizedKuroIntroProps> = (props) => {
  const isMobile = useIsMobile();
  const { shouldReduceAnimations } = useOptimizedAnimations();

  // Use lightweight intro on mobile or when animations should be reduced
  if (isMobile || shouldReduceAnimations) {
    return <LightweightIntro {...props} />;
  }

  // Use full animated intro on desktop
  return <AnimatedIntro {...props} />;
};

export default OptimizedKuroIntro;