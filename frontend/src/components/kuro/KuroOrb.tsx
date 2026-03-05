import { useRef, useEffect, useState, useCallback, memo } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface KuroOrbProps {
  size?: number;
  className?: string;
  intensity?: 'subtle' | 'normal' | 'vibrant';
}

/**
 * KuroOrb - A living, cursor-following orb entity
 * Inspired by GitHub's homepage animation
 * 
 * Features:
 * - Spring-based cursor tracking with inertia
 * - Proximity-based size reactions
 * - Idle breathing animation
 * - Click ripple effects
 * - Internal gradient drift
 */
export const KuroOrb = memo(function KuroOrb({ 
  size = 200, 
  className = '',
  intensity = 'normal'
}: KuroOrbProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [isClicked, setIsClicked] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  
  // Spring physics for smooth cursor tracking
  const springConfig = { damping: 25, stiffness: 150, mass: 1 };
  const mouseX = useSpring(0, springConfig);
  const mouseY = useSpring(0, springConfig);
  
  // Transform mouse position to orb offset (subtle movement)
  const orbX = useTransform(mouseX, (val) => val * 0.15);
  const orbY = useTransform(mouseY, (val) => val * 0.15);
  
  // Track cursor globally
  useEffect(() => {
    setIsMounted(true);
    
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      
      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      
      // Calculate offset from center
      const offsetX = e.clientX - centerX;
      const offsetY = e.clientY - centerY;
      
      mouseX.set(offsetX);
      mouseY.set(offsetY);
      
      // Check proximity for hover effect
      const distance = Math.sqrt(offsetX * offsetX + offsetY * offsetY);
      setIsHovered(distance < size * 1.5);
    };
    
    const handleClick = () => {
      setIsClicked(true);
      setTimeout(() => setIsClicked(false), 300);
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('click', handleClick);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('click', handleClick);
    };
  }, [mouseX, mouseY, size]);
  
  // Intensity-based opacity values
  const opacityMap = {
    subtle: { base: 0.4, glow: 0.2 },
    normal: { base: 0.6, glow: 0.35 },
    vibrant: { base: 0.8, glow: 0.5 }
  };
  
  const { base: baseOpacity, glow: glowOpacity } = opacityMap[intensity];
  
  return (
    <div 
      ref={containerRef}
      className={`relative ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Outer glow layer */}
      <motion.div
        className="absolute inset-0 rounded-full"
        style={{
          x: orbX,
          y: orbY,
          background: `radial-gradient(circle, 
            rgba(59, 130, 246, ${glowOpacity}) 0%, 
            rgba(139, 92, 246, ${glowOpacity * 0.6}) 40%,
            transparent 70%)`,
          filter: 'blur(40px)',
        }}
        animate={{
          scale: isHovered ? 1.2 : isClicked ? 0.9 : 1,
          opacity: isMounted ? 1 : 0,
        }}
        transition={{
          scale: { type: 'spring', damping: 20, stiffness: 200 },
          opacity: { duration: 0.8 }
        }}
      />
      
      {/* Core orb */}
      <motion.div
        className="absolute inset-0 rounded-full overflow-hidden"
        style={{
          x: orbX,
          y: orbY,
        }}
        animate={{
          scale: isHovered ? 1.08 : isClicked ? 0.95 : 1,
        }}
        transition={{ type: 'spring', damping: 20, stiffness: 200 }}
      >
        {/* Glassy surface */}
        <div 
          className="absolute inset-0 rounded-full"
          style={{
            background: `radial-gradient(circle at 30% 30%, 
              rgba(255, 255, 255, 0.12) 0%,
              rgba(59, 130, 246, ${baseOpacity * 0.3}) 30%,
              rgba(139, 92, 246, ${baseOpacity * 0.2}) 60%,
              rgba(0, 0, 0, 0.4) 100%)`,
            border: '1px solid rgba(255, 255, 255, 0.1)',
            boxShadow: `
              inset 0 0 60px rgba(59, 130, 246, 0.15),
              inset 0 0 20px rgba(139, 92, 246, 0.1),
              0 0 30px rgba(59, 130, 246, ${glowOpacity * 0.5})
            `,
          }}
        />
        
        {/* Internal gradient animation - Plasma effect */}
        <motion.div
          className="absolute inset-4 rounded-full"
          style={{
            background: `conic-gradient(from 0deg at 50% 50%, 
              rgba(59, 130, 246, 0.4) 0deg,
              rgba(139, 92, 246, 0.3) 90deg,
              rgba(59, 130, 246, 0.2) 180deg,
              rgba(139, 92, 246, 0.4) 270deg,
              rgba(59, 130, 246, 0.4) 360deg)`,
            filter: 'blur(20px)',
          }}
          animate={{
            rotate: [0, 360],
          }}
          transition={{
            rotate: {
              duration: 20,
              repeat: Infinity,
              ease: 'linear',
            },
          }}
        />
        
        {/* Inner glow core */}
        <motion.div
          className="absolute rounded-full"
          style={{
            top: '25%',
            left: '25%',
            width: '50%',
            height: '50%',
            background: `radial-gradient(circle,
              rgba(255, 255, 255, 0.15) 0%,
              rgba(59, 130, 246, 0.3) 40%,
              transparent 70%)`,
            filter: 'blur(10px)',
          }}
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.6, 0.8, 0.6],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        
        {/* Breathing pulse */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            border: '1px solid rgba(59, 130, 246, 0.2)',
          }}
          animate={{
            scale: [1, 1.02, 1],
            opacity: [0.5, 0.8, 0.5],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </motion.div>
      
      {/* Click ripple effect */}
      {isClicked && (
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            border: '2px solid rgba(59, 130, 246, 0.5)',
          }}
          initial={{ scale: 1, opacity: 0.8 }}
          animate={{ scale: 1.5, opacity: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      )}
    </div>
  );
});

export default KuroOrb;
