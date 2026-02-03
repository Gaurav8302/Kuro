import { memo } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';

interface KuroAvatarProps {
  size?: number;
  followCursor?: boolean;
  animated?: boolean;
  className?: string;
  showGlow?: boolean;
}

/**
 * KuroAvatar - The Kuro AI bot avatar
 * Can optionally follow cursor with spring physics
 * Uses the actual kuroai.png image as the avatar
 */
export const KuroAvatar = memo(function KuroAvatar({
  size = 80,
  followCursor = false,
  animated = true,
  className = '',
  showGlow = true,
}: KuroAvatarProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  // Spring physics for cursor following
  const springConfig = { damping: 30, stiffness: 150, mass: 1 };
  const mouseX = useSpring(0, springConfig);
  const mouseY = useSpring(0, springConfig);

  // Transform mouse position to avatar offset
  const avatarX = useTransform(mouseX, (val) => val * 0.12);
  const avatarY = useTransform(mouseY, (val) => val * 0.12);

  useEffect(() => {
    setIsMounted(true);

    if (!followCursor) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const offsetX = e.clientX - centerX;
      const offsetY = e.clientY - centerY;

      mouseX.set(offsetX);
      mouseY.set(offsetY);

      // Check proximity for hover effect
      const distance = Math.sqrt(offsetX * offsetX + offsetY * offsetY);
      setIsHovered(distance < size * 2);
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [followCursor, mouseX, mouseY, size]);

  return (
    <div
      ref={containerRef}
      className={`relative ${className}`}
      style={{ width: size, height: size }}
    >
      {/* Outer glow */}
      {showGlow && (
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            x: followCursor ? avatarX : 0,
            y: followCursor ? avatarY : 0,
            background: `radial-gradient(circle, 
              rgba(59, 130, 246, 0.3) 0%, 
              rgba(139, 92, 246, 0.2) 50%,
              transparent 70%)`,
            filter: 'blur(20px)',
          }}
          animate={{
            scale: isHovered ? 1.3 : animated ? [1, 1.15, 1] : 1,
            opacity: isMounted ? (isHovered ? 0.8 : 0.5) : 0,
          }}
          transition={{
            scale: isHovered 
              ? { type: 'spring', damping: 20, stiffness: 200 }
              : { duration: 3, repeat: Infinity, ease: 'easeInOut' },
            opacity: { duration: 0.5 },
          }}
        />
      )}

      {/* Avatar container */}
      <motion.div
        className="relative w-full h-full rounded-full overflow-hidden"
        style={{
          x: followCursor ? avatarX : 0,
          y: followCursor ? avatarY : 0,
          border: '2px solid rgba(59, 130, 246, 0.3)',
          boxShadow: showGlow ? `
            0 0 20px rgba(59, 130, 246, 0.2),
            inset 0 0 20px rgba(59, 130, 246, 0.1)
          ` : 'none',
        }}
        animate={{
          scale: isHovered ? 1.05 : 1,
        }}
        transition={{ type: 'spring', damping: 20, stiffness: 200 }}
      >
        {/* Avatar image */}
        <img
          src="/kuroai.png"
          alt="Kuro AI"
          className="w-full h-full object-cover"
          style={{
            filter: animated ? undefined : 'none',
          }}
        />

        {/* Subtle overlay for depth */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: `radial-gradient(circle at 30% 30%, 
              rgba(255, 255, 255, 0.1) 0%,
              transparent 50%)`,
          }}
        />
      </motion.div>

      {/* Breathing ring animation */}
      {animated && (
        <motion.div
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{
            border: '1px solid rgba(59, 130, 246, 0.2)',
          }}
          animate={{
            scale: [1, 1.08, 1],
            opacity: [0.5, 0.2, 0.5],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}
    </div>
  );
});

export default KuroAvatar;
