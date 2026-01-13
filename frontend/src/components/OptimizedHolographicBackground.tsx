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

// Full animated background for desktop - optimized for performance
const AnimatedBackground: React.FC<OptimizedHolographicBackgroundProps> = memo(({ variant = 'default', className = '' }) => {
  const { enableParticles, particleCount } = useOptimizedAnimations();

  // Memoize particles to prevent recalculation on every render
  const particles = useMemo(() => {
    if (!enableParticles) return [];
    
    const colors = {
      default: ['#00e6d6', '#8c1aff', '#1a8cff'],
      intense: ['#00ffff', '#ff00ff', '#0080ff'],
      subtle: ['#004d4d', '#4d004d', '#004080']
    };

    return Array.from({ length: particleCount }, (_, i) => ({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 2 + 1,
      color: colors[variant][i % colors[variant].length],
      animationDelay: `${Math.random() * 4}s`,
      animationDuration: `${3 + Math.random() * 2}s`
    }));
  }, [variant, particleCount, enableParticles]);

  return (
    <div className={`fixed inset-0 pointer-events-none ${className}`}>
      {/* CSS-animated particles for desktop - no JS animation overhead */}
      {enableParticles && particles.map(particle => (
        <div
          key={particle.id}
          className="absolute rounded-full animate-particle-float"
          style={{
            left: `${particle.x}%`,
            top: `${particle.y}%`,
            width: particle.size,
            height: particle.size,
            backgroundColor: particle.color,
            opacity: 0.3,
            boxShadow: `0 0 ${particle.size}px ${particle.color}`,
            animationDelay: particle.animationDelay,
            animationDuration: particle.animationDuration,
            willChange: 'transform'
          }}
        />
      ))}
      
      {/* Static gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-holo-cyan-500/5 via-holo-purple-500/5 to-holo-blue-500/5" />
      
      {/* Static mesh gradient - no animation needed */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          background: `
            radial-gradient(circle at 25% 25%, rgba(0, 230, 214, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 75% 75%, rgba(140, 26, 255, 0.08) 0%, transparent 50%)
          `,
        }}
      />
      
      {/* Scan lines */}
      <div className="absolute inset-0 scan-lines opacity-10" />
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