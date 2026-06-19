import { memo } from 'react';
import { motion } from 'framer-motion';
import { useOptimizedAnimations } from '../../hooks/use-performance';

interface KuroBackgroundProps {
  variant?: 'default' | 'subtle' | 'hero';
  className?: string;
}

export const KuroBackground = memo(function KuroBackground({
  variant = 'default',
  className = '',
}: KuroBackgroundProps) {
  const { shouldReduceAnimations } = useOptimizedAnimations();

  return (
    <div className={`fixed inset-0 -z-10 overflow-hidden bg-background ${className}`}>
      <div className="absolute inset-0 kuro-gradient" />
      <div className="absolute inset-0 noise-overlay" />

      {(variant === 'hero' || variant === 'default') && (
        <>
          {shouldReduceAnimations ? (
            <>
              <div
                className="absolute w-[600px] h-[600px] rounded-full opacity-20 blur-[100px]"
                style={{
                  background: 'radial-gradient(circle, hsl(var(--primary) / 0.5) 0%, transparent 70%)',
                  top: '-10%',
                  right: '-10%',
                  transform: 'translateZ(0)',
                }}
              />
              <div
                className="absolute w-[500px] h-[500px] rounded-full opacity-15 blur-[100px]"
                style={{
                  background: 'radial-gradient(circle, hsl(var(--accent) / 0.5) 0%, transparent 70%)',
                  bottom: '5%',
                  left: '-5%',
                  transform: 'translateZ(0)',
                }}
              />
            </>
          ) : (
            <>
              <motion.div
                className="absolute w-[600px] h-[600px] rounded-full opacity-20 blur-[100px]"
                style={{
                  background: 'radial-gradient(circle, hsl(var(--primary) / 0.5) 0%, transparent 70%)',
                  top: '-10%',
                  right: '-10%',
                  willChange: 'transform',
                }}
                animate={{
                  x: [0, 30, 0],
                  y: [0, 20, 0],
                }}
                transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut' }}
              />
              <motion.div
                className="absolute w-[500px] h-[500px] rounded-full opacity-15 blur-[100px]"
                style={{
                  background: 'radial-gradient(circle, hsl(var(--accent) / 0.5) 0%, transparent 70%)',
                  bottom: '5%',
                  left: '-5%',
                  willChange: 'transform',
                }}
                animate={{
                  x: [0, -30, 0],
                  y: [0, -40, 0],
                }}
                transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
              />
            </>
          )}
        </>
      )}

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
