import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

interface BackgroundProps {
  variant?: 'minimal' | 'standard' | 'rich';
  className?: string;
}

export const PerformanceOptimizedBackground: React.FC<BackgroundProps> = ({
  variant = 'standard',
  className = ''
}) => {
  // Memoize particle configuration to prevent re-renders
  const particleConfig = useMemo(() => {
    const configs = {
      minimal: { count: 8, size: [1, 2], opacity: [0.1, 0.3] },
      standard: { count: 15, size: [1, 3], opacity: [0.2, 0.4] },
      rich: { count: 25, size: [2, 4], opacity: [0.3, 0.5] }
    };
    return configs[variant];
  }, [variant]);

  const particles = useMemo(() => 
    Array.from({ length: particleConfig.count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: Math.random() * (particleConfig.size[1] - particleConfig.size[0]) + particleConfig.size[0],
      opacity: Math.random() * (particleConfig.opacity[1] - particleConfig.opacity[0]) + particleConfig.opacity[0],
      duration: 8 + Math.random() * 12,
      delay: Math.random() * 5
    })),
    [particleConfig]
  );

  return (
    <div className={`fixed inset-0 pointer-events-none overflow-hidden ${className}`}>
      {/* Static gradient base */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-secondary/5" />
      
      {/* Animated mesh gradient - reduced complexity for mobile */}
      <motion.div
        className="absolute inset-0 opacity-40"
        style={{
          background: `
            radial-gradient(circle at 30% 40%, rgba(var(--primary), 0.1) 0%, transparent 50%),
            radial-gradient(circle at 70% 60%, rgba(var(--secondary), 0.08) 0%, transparent 50%)
          `
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
      
      {/* Optimized particles */}
      {variant !== 'minimal' && (
        <div className="absolute inset-0">
          {particles.map(particle => (
            <motion.div
              key={particle.id}
              className="absolute rounded-full bg-primary"
              style={{
                left: `${particle.left}%`,
                top: `${particle.top}%`,
                width: particle.size,
                height: particle.size,
                opacity: particle.opacity,
                filter: 'blur(0.5px)'
              }}
              animate={{
                y: [-10, -30, -10],
                x: [-5, 5, -5],
                scale: [1, 1.1, 1]
              }}
              transition={{
                duration: particle.duration,
                repeat: Infinity,
                delay: particle.delay,
                ease: 'easeInOut'
              }}
            />
          ))}
        </div>
      )}
      
      {/* Subtle grid overlay */}
      <div 
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(rgba(var(--primary), 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(var(--primary), 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px'
        }}
      />
    </div>
  );
};

export default PerformanceOptimizedBackground;