import { memo } from 'react';
import { motion } from 'framer-motion';

interface KuroBackgroundProps {
  variant?: 'default' | 'subtle' | 'hero';
  className?: string;
}

/**
 * KuroBackground - Professional dark background with animated orbs
 * Clean, calm, and modern
 */
export const KuroBackground = memo(function KuroBackground({
  variant = 'default',
  className = '',
}: KuroBackgroundProps) {
  return (
    <div className={`fixed inset-0 -z-10 overflow-hidden bg-background ${className}`}>
      {/* Kuro gradient background */}
      <div className="absolute inset-0 kuro-gradient" />
      
      {/* Noise overlay */}
      <div className="absolute inset-0 noise-overlay" />

      {/* Animated orbs for hero/default variants */}
      {(variant === 'hero' || variant === 'default') && (
        <>
          {/* Primary orb - top right */}
          <motion.div
            className="absolute w-[600px] h-[600px] rounded-full opacity-20 blur-[100px]"
            style={{
              background: 'radial-gradient(circle, hsl(var(--primary) / 0.5) 0%, transparent 70%)',
              top: '-10%',
              right: '-10%',
            }}
            animate={{
              x: [0, 30, 0],
              y: [0, 20, 0],
            }}
            transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }}
          />

          {/* Secondary orb - bottom left */}
          <motion.div
            className="absolute w-[500px] h-[500px] rounded-full opacity-15 blur-[100px]"
            style={{
              background: 'radial-gradient(circle, hsl(var(--accent) / 0.5) 0%, transparent 70%)',
              bottom: '5%',
              left: '-5%',
            }}
            animate={{
              x: [0, -30, 0],
              y: [0, -40, 0],
            }}
            transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
          />
        </>
      )}

      {/* Grid pattern for hero variant */}
      {variant === 'hero' && (
        <div 
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `
              linear-gradient(to right, hsl(var(--foreground)) 1px, transparent 1px),
              linear-gradient(to bottom, hsl(var(--foreground)) 1px, transparent 1px)
            `,
            backgroundSize: '60px 60px',
          }}
        />
      )}
    </div>
  );
});

export default KuroBackground;
