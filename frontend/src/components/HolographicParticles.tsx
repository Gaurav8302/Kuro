import React, { useMemo } from 'react';

interface ParticleProps {
  count?: number;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  colors?: string[];
  speed?: 'slow' | 'medium' | 'fast';
}

export const HolographicParticles: React.FC<ParticleProps> = ({
  count = 20, // Reduced default count
  className = '',
  size = 'md',
  colors = ['#00e6d6', '#8c1aff', '#1a8cff'],
  speed = 'medium'
}) => {
  const particles = useMemo(() => {
    const sizeMap = { sm: [1, 2], md: [2, 4], lg: [3, 6] };
    const speedMap = { slow: [6, 10], medium: [4, 8], fast: [2, 5] };
    
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: Math.random() * (sizeMap[size][1] - sizeMap[size][0]) + sizeMap[size][0],
      color: colors[i % colors.length],
      duration: Math.random() * (speedMap[speed][1] - speedMap[speed][0]) + speedMap[speed][0],
      delay: Math.random() * 4,
      opacity: Math.random() * 0.4 + 0.2
    }));
  }, [count, size, colors, speed]);

  return (
    <div className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`}>
      {particles.map(particle => (
        <div
          key={particle.id}
          className="absolute rounded-full animate-particle-float"
          style={{
            left: `${particle.left}%`,
            top: `${particle.top}%`,
            width: particle.size,
            height: particle.size,
            backgroundColor: particle.color,
            opacity: particle.opacity,
            boxShadow: `0 0 ${particle.size}px ${particle.color}`,
            animationDuration: `${particle.duration}s`,
            animationDelay: `${particle.delay}s`,
            willChange: 'transform'
          }}
        />
      ))}
    </div>
  );
};

export default HolographicParticles;