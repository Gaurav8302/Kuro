import { useState, useEffect, useRef, useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

interface Particle {
  id: number;
  left: number;
  top: number;
  size: number;
  delay: number;
  duration: number;
  opacity: number;
}

interface KuroIntroProps {
  phrases?: string[];
  cycleMs?: number;
  fullscreen?: boolean; // if false, renders embeddable hero-sized variant
  className?: string;
  onFinish?: () => void; // optional callback when component auto cycles through once (optional future use)
}

// Full‑screen intro animation for Kuro AI (React + Vite compatible)
const KuroIntro: React.FC<KuroIntroProps> = ({ phrases = ["Let's Imagine", "Let's Build", 'Kuro AI'], cycleMs = 1800, fullscreen = true, className, onFinish }) => {
  const [index, setIndex] = useState(0);
  const mounted = useRef(false);

  // Pre-generate particles once
  const particles: Particle[] = useMemo(() => (
    Array.from({ length: 28 }).map((_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: 4 + Math.random() * 8,
      delay: Math.random() * 8,
      duration: 12 + Math.random() * 18,
      opacity: 0.15 + Math.random() * 0.25
    }))
  ), []);

  useEffect(() => {
    mounted.current = true;
    const interval = setInterval(() => {
      setIndex(prev => {
        const next = (prev + 1) % phrases.length;
        // If we've completed a full cycle, invoke onFinish once
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
    <div className={[
      fullscreen
        ? 'fixed inset-0 z-[9999]'
        : 'relative w-full h-[420px] md:h-[520px] rounded-3xl overflow-hidden shadow-glow'
      , 'overflow-hidden select-none', className].filter(Boolean).join(' ')}>
      {/* Base gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-black via-[#0d0d1a] to-[#1a0033]" />

      {/* Animated hue-shift radial glow */}
      <div className="absolute inset-0 mix-blend-screen opacity-60 animate-kuro-hue">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_40%,rgba(120,40,255,0.35),transparent_60%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_60%,rgba(0,140,255,0.25),transparent_65%)]" />
      </div>

      {/* Subtle moving gradient veil */}
      <div className="pointer-events-none absolute inset-0 animate-kuro-wave opacity-[0.35]" style={{
        background: 'linear-gradient(120deg, rgba(147,51,234,0.15), rgba(59,130,246,0.12), rgba(147,51,234,0.15))',
        backgroundSize: '300% 300%'
      }} />

      {/* Particle / bokeh layer */}
      <div className="absolute inset-0">
        {particles.map(p => (
          <span
            key={p.id}
            className="absolute rounded-full bg-purple-400/30 blur-[2px] animate-kuro-float"
            style={{
              left: `${p.left}vw`,
              top: `${p.top}vh`,
              width: p.size,
              height: p.size,
              animationDelay: `${p.delay}s`,
              animationDuration: `${p.duration}s`,
              opacity: p.opacity
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
                initial={{ opacity: 0, scale: 0.94, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.92, y: -8 }}
                transition={{ duration: 0.7, ease: [0.25, 0.8, 0.25, 1] }}
                className={fullscreen
                  ? 'font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-fuchsia-400 to-indigo-400 drop-shadow-[0_0_10px_rgba(147,51,234,0.8)] text-5xl md:text-7xl'
                  : 'font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-fuchsia-400 to-indigo-400 drop-shadow-[0_0_8px_rgba(147,51,234,0.7)] text-4xl md:text-6xl'
                }
              >
                {phrase}
              </motion.h1>
            </AnimatePresence>

            {/* Underline pulse accent */}
            <motion.div
              key={`underline-${phrase}`}
              initial={{ opacity: 0, scaleX: 0.3 }}
              animate={{ opacity: 0.85, scaleX: 1 }}
              exit={{ opacity: 0, scaleX: 0.2 }}
              transition={{ duration: 0.8, delay: 0.15 }}
              className="mx-auto mt-4 h-[3px] w-32 origin-center rounded-full bg-gradient-to-r from-purple-500 via-fuchsia-400 to-indigo-400 shadow-[0_0_12px_rgba(147,51,234,0.8)]"
            />
          </div>

          {fullscreen && (
            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 0.6, y: 0 }}
              transition={{ delay: 0.4, duration: 0.8 }}
              className="mt-10 max-w-xl text-sm md:text-base text-white/60 leading-relaxed"
            >
              A creative co‑pilot for builders, dreamers & problem solvers.
            </motion.p>
          )}
        </div>
      </div>

      {fullscreen && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-black via-black/40 to-transparent" />
      )}

      <style>{`
        .animate-kuro-hue { animation: kuroHue 12s linear infinite; }
        .animate-kuro-wave { animation: kuroWave 18s ease-in-out infinite; }
  .animate-kuro-float { animation: kuroFloat linear infinite; }
        @keyframes kuroHue { 0%{filter:hue-rotate(0deg)} 100%{filter:hue-rotate(360deg)} }
        @keyframes kuroWave { 0%,100%{transform:translate3d(0,0,0)} 50%{transform:translate3d(-8%,4%,0)} }
        @keyframes kuroFloat { 0% { transform: translateY(0) translateX(0) scale(1); } 25% { transform: translateY(-12vh) translateX(4vw) scale(1.15); } 50% { transform: translateY(-24vh) translateX(-2vw) scale(0.9); } 75% { transform: translateY(-36vh) translateX(3vw) scale(1.1); } 100% { transform: translateY(-48vh) translateX(0) scale(1); } }
      `}</style>
    </div>
  );
};

export default KuroIntro;

export function useKuroIntro(durationMs = 4000) {
  const [show, setShow] = useState(true);
  useEffect(() => { const t = setTimeout(() => setShow(false), durationMs); return () => clearTimeout(t); }, [durationMs]);
  return { show, hide: () => setShow(false) };
}
