import React, { memo, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useIsMobile } from '@/hooks/use-mobile';
import { useOptimizedAnimations } from '@/hooks/use-performance';

interface OptimizedHolographicBackgroundProps {
  variant?: 'default' | 'intense' | 'subtle';
  className?: string;
}

// Lightweight CSS-only background for mobile
const CSSOnlyBackground: React.FC<{ variant: string; className: string }> = memo(({ variant, className }) => (
  <div className={`fixed inset-0 pointer-events-none ${className}`}>
    {/* Static gradient overlay optimized for mobile */}
    <div className={`absolute inset-0 ${
      variant === 'intense' 
        ? 'bg-gradient-to-br from-holo-cyan-500/10 via-holo-purple-500/10 to-holo-blue-500/10'
        : variant === 'subtle'
        ? 'bg-gradient-to-br from-holo-cyan-500/3 via-holo-purple-500/3 to-holo-blue-500/3'
        : 'bg-gradient-to-br from-holo-cyan-500/5 via-holo-purple-500/5 to-holo-blue-500/5'
    }`} />
    
    {/* Simple CSS grid pattern */}
    <div 
      className="absolute inset-0 opacity-20"
      style={{
        backgroundImage: `
          linear-gradient(rgba(0, 230, 214, 0.1) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0, 230, 214, 0.1) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px'
      }}
    />
  </div>
));


// Enhanced: Add parallax mesh, more layers for desktop, minimal for mobile
const AnimatedBackground: React.FC<OptimizedHolographicBackgroundProps> = memo(({ variant = 'default', className = '' }) => {
  const { enableParticles, particleCount, enableComplexAnimations } = useOptimizedAnimations();

  // Parallax mesh layers for desktop
  const meshLayers = enableComplexAnimations ? [
    { className: 'absolute inset-0 opacity-20', style: { background: 'radial-gradient(circle at 30% 40%, rgba(0,230,214,0.08) 0%, transparent 60%)', backgroundSize: '100% 100%' } },
    { className: 'absolute inset-0 opacity-10', style: { background: 'radial-gradient(circle at 70% 60%, rgba(140,26,255,0.08) 0%, transparent 60%)', backgroundSize: '100% 100%' } },
    { className: 'absolute inset-0 opacity-10', style: { background: 'radial-gradient(circle at 50% 80%, rgba(26,140,255,0.06) 0%, transparent 60%)', backgroundSize: '100% 100%' } },
  ] : [];

  const particles = useMemo(() => {
    if (!enableParticles) return [];
    const colors = {
      default: ['#00e6d6', '#8c1aff', '#1a8cff', '#ff1ab1', '#1aff1a'],
      intense: ['#00ffff', '#ff00ff', '#0080ff', '#ff0080', '#80ff00'],
      subtle: ['#004d4d', '#4d004d', '#004080', '#4d0026', '#264d00']
    };
    return Array.from({ length: particleCount }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: enableComplexAnimations ? Math.random() * 3 + 1 : Math.random() * 1.5 + 0.5,
      color: colors[variant][Math.floor(Math.random() * colors[variant].length)],
      speed: enableComplexAnimations ? Math.random() * 0.5 + 0.1 : Math.random() * 0.2 + 0.1,
      direction: Math.random() * Math.PI * 2,
      opacity: enableComplexAnimations ? Math.random() * 0.5 + 0.1 : Math.random() * 0.3 + 0.05
    }));
  }, [variant, particleCount, enableParticles, enableComplexAnimations]);

  return (
    <div className={`fixed inset-0 pointer-events-none ${className}`}>
      {/* Animated particles for desktop, lighter for mobile */}
      {enableParticles && particles.map(particle => (
        <motion.div
          key={particle.id}
          className="absolute rounded-full"
          style={{
            left: `${particle.x}%`,
            top: `${particle.y}%`,
            width: particle.size,
            height: particle.size,
            backgroundColor: particle.color,
            opacity: particle.opacity,
            boxShadow: enableComplexAnimations ? `0 0 ${particle.size * 2}px ${particle.color}` : undefined,
            filter: enableComplexAnimations ? 'blur(0.5px)' : undefined
          }}
          animate={enableComplexAnimations ? {
            y: [-20, -40, -20],
            x: [-10, 10, -10],
            scale: [1, 1.2, 1],
            opacity: [particle.opacity, particle.opacity * 1.5, particle.opacity]
          } : {
            y: [0, 0],
            x: [0, 0],
            scale: [1, 1],
            opacity: [particle.opacity, particle.opacity]
          }}
          transition={{
            duration: particle.speed * (enableComplexAnimations ? 10 : 4),
            repeat: Infinity,
            delay: Math.random() * 5,
            ease: enableComplexAnimations ? 'easeInOut' : 'linear'
          }}
        />
      ))}

      {/* Parallax mesh layers for desktop only */}
      {meshLayers.map((layer, i) => (
        <motion.div key={i} className={layer.className} style={layer.style}
          animate={enableComplexAnimations ? { opacity: [0.1, 0.2, 0.1] } : undefined }
          transition={enableComplexAnimations ? { duration: 12 + i * 2, repeat: Infinity, ease: 'easeInOut' } : undefined }
        />
      ))}

      {/* Static gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-holo-cyan-500/5 via-holo-purple-500/5 to-holo-blue-500/5" />

      {/* Animated mesh gradient for desktop only */}
      {enableComplexAnimations && (
        <motion.div
          className="absolute inset-0 opacity-30"
          style={{
            background: `
              radial-gradient(circle at 25% 25%, rgba(0, 230, 214, 0.1) 0%, transparent 50%),
              radial-gradient(circle at 75% 75%, rgba(140, 26, 255, 0.1) 0%, transparent 50%),
              radial-gradient(circle at 50% 50%, rgba(26, 140, 255, 0.05) 0%, transparent 50%)
            `,
            backgroundSize: '100% 100%'
          }}
          animate={{
            backgroundPosition: ['0% 0%', '100% 100%', '0% 0%']
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: 'linear'
          }}
        />
      )}

      {/* Scan lines */}
      <div className="absolute inset-0 scan-lines opacity-20" />
    </div>
  );
});

export const OptimizedHolographicBackground: React.FC<OptimizedHolographicBackgroundProps> = ({ 
  variant = 'default', 
  className = '' 
}) => {
  const isMobile = useIsMobile();
  const { shouldReduceAnimations } = useOptimizedAnimations();

  // Use CSS-only background on mobile or when animations should be reduced
  if (isMobile || shouldReduceAnimations) {
    return <CSSOnlyBackground variant={variant} className={className} />;
  }

  // Use full animated background on desktop
  return <AnimatedBackground variant={variant} className={className} />;
};

export default OptimizedHolographicBackground;