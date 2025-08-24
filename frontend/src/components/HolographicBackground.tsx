import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  color: string;
  speed: number;
  direction: number;
  opacity: number;
}

interface HolographicBackgroundProps {
  variant?: 'default' | 'intense' | 'subtle';
  particleCount?: number;
  className?: string;
}

export const HolographicBackground: React.FC<HolographicBackgroundProps> = ({
  variant = 'default',
  particleCount = 50,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const particlesRef = useRef<Particle[]>([]);

  const colors = {
    default: ['#00e6d6', '#8c1aff', '#1a8cff', '#ff1ab1', '#1aff1a'],
    intense: ['#00ffff', '#ff00ff', '#0080ff', '#ff0080', '#80ff00'],
    subtle: ['#004d4d', '#4d004d', '#004080', '#4d0026', '#264d00']
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    const createParticles = () => {
      const particles: Particle[] = [];
      const selectedColors = colors[variant];
      
      for (let i = 0; i < particleCount; i++) {
        particles.push({
          id: i,
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          size: Math.random() * 3 + 1,
          color: selectedColors[Math.floor(Math.random() * selectedColors.length)],
          speed: Math.random() * 0.5 + 0.1,
          direction: Math.random() * Math.PI * 2,
          opacity: Math.random() * 0.5 + 0.1
        });
      }
      
      particlesRef.current = particles;
    };

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particlesRef.current.forEach(particle => {
        // Update position
        particle.x += Math.cos(particle.direction) * particle.speed;
        particle.y += Math.sin(particle.direction) * particle.speed;
        
        // Wrap around edges
        if (particle.x < 0) particle.x = canvas.width;
        if (particle.x > canvas.width) particle.x = 0;
        if (particle.y < 0) particle.y = canvas.height;
        if (particle.y > canvas.height) particle.y = 0;
        
        // Pulse opacity
        particle.opacity += (Math.random() - 0.5) * 0.02;
        particle.opacity = Math.max(0.1, Math.min(0.6, particle.opacity));
        
        // Draw particle with glow effect
        ctx.save();
        ctx.globalAlpha = particle.opacity;
        ctx.shadowBlur = 20;
        ctx.shadowColor = particle.color;
        ctx.fillStyle = particle.color;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      });
      
      animationRef.current = requestAnimationFrame(animate);
    };

    resizeCanvas();
    createParticles();
    animate();

    window.addEventListener('resize', resizeCanvas);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [variant, particleCount]);

  return (
    <div className={`fixed inset-0 pointer-events-none ${className}`}>
      <canvas
        ref={canvasRef}
        className="absolute inset-0 opacity-60"
        style={{ mixBlendMode: 'screen' }}
      />
      
      {/* Static gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-holo-cyan-500/5 via-holo-purple-500/5 to-holo-blue-500/5" />
      
      {/* Animated mesh gradient */}
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
      
      {/* Scan lines */}
      <div className="absolute inset-0 scan-lines opacity-20" />
    </div>
  );
};

export default HolographicBackground;