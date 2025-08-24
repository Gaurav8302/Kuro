import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

interface ParticleProps {
  count?: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  colors?: string[];
  speed?: 'slow' | 'medium' | 'fast';
}

export const HolographicParticles: React.FC<ParticleProps> = ({
  count = 30,
  className = '',
  size = 'md',
  colors = ['#00e6d6', '#8c1aff', '#1a8cff', '#ff1ab1'],
  speed = 'medium'
}) => {
  const particles = useMemo(() => {
    const sizeMap = { sm: [1, 3], md: [2, 5], lg: [3, 8] };
    const speedMap = { slow: [8, 15], medium: [5, 12], fast: [3, 8] };
    
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: Math.random() * (sizeMap[size][1] - sizeMap[size][0]) + sizeMap[size][0],
      color: colors[Math.floor(Math.random() * colors.length)],
      duration: Math.random() * (speedMap[speed][1] - speedMap[speed][0]) + speedMap[speed][0],
      delay: Math.random() * 5,
      opacity: Math.random() * 0.6 + 0.2
    }));
  }, [count, size, colors, speed]);

  return (
    <div className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`}>
      {particles.map(particle => (
        <motion.div
          key={particle.id}
          className="absolute rounded-full"
          style={{
            left: `${particle.left}%`,
            top: `${particle.top}%`,
            width: particle.size,
            height: particle.size,
            backgroundColor: particle.color,
            opacity: particle.opacity,
            boxShadow: `0 0 ${particle.size * 2}px ${particle.color}`,
            filter: 'blur(0.5px)'
          }}
          animate={{
            y: [-20, -40, -20],
            x: [-10, 10, -10],
            scale: [1, 1.2, 1],
            opacity: [particle.opacity, particle.opacity * 1.5, particle.opacity]
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
  );
};

export default HolographicParticles;