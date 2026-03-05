import { memo, useRef, useEffect, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface KuroBotProps {
  size?: number;
  className?: string;
}

/**
 * KuroBot - 3D-style Kuro AI bot
 * The head follows the cursor while the body remains stationary
 * Inspired by the Kuro profile image aesthetic
 */
export const KuroBot = memo(function KuroBot({
  size = 160,
  className = '',
}: KuroBotProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  // Spring physics for smooth head movement
  const springConfig = { damping: 25, stiffness: 120, mass: 0.8 };
  const mouseX = useSpring(0, springConfig);
  const mouseY = useSpring(0, springConfig);

  // Transform mouse position to head rotation (limited range for natural look)
  const headRotateY = useTransform(mouseX, [-400, 400], [-25, 25]);
  const headRotateX = useTransform(mouseY, [-300, 300], [15, -15]);
  
  // Subtle eye movement following cursor
  const eyeOffsetX = useTransform(mouseX, [-400, 400], [-3, 3]);
  const eyeOffsetY = useTransform(mouseY, [-300, 300], [-2, 2]);

  useEffect(() => {
    setIsMounted(true);

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const offsetX = e.clientX - centerX;
      const offsetY = e.clientY - centerY;

      mouseX.set(offsetX);
      mouseY.set(offsetY);

      // Check proximity for glow effect
      const distance = Math.sqrt(offsetX * offsetX + offsetY * offsetY);
      setIsHovered(distance < size * 2.5);
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY, size]);

  const bodyHeight = size * 0.6;
  const headSize = size * 0.55;
  const neckHeight = size * 0.08;

  return (
    <div
      ref={containerRef}
      className={`relative flex flex-col items-center ${className}`}
      style={{ 
        width: size, 
        height: size + bodyHeight * 0.3,
        perspective: '800px',
      }}
    >
      {/* Ambient glow behind the bot */}
      <motion.div
        className="absolute"
        style={{
          width: size * 1.5,
          height: size * 1.5,
          top: '10%',
          left: '50%',
          x: '-50%',
          background: `radial-gradient(circle, 
            rgba(59, 130, 246, 0.25) 0%, 
            rgba(139, 92, 246, 0.15) 40%,
            transparent 70%)`,
          filter: 'blur(30px)',
        }}
        animate={{
          scale: isHovered ? 1.2 : [1, 1.1, 1],
          opacity: isMounted ? (isHovered ? 0.8 : 0.5) : 0,
        }}
        transition={{
          scale: isHovered 
            ? { type: 'spring', damping: 20, stiffness: 200 }
            : { duration: 3, repeat: Infinity, ease: 'easeInOut' },
          opacity: { duration: 0.5 },
        }}
      />

      {/* HEAD - Follows cursor */}
      <motion.div
        className="relative z-10"
        style={{
          width: headSize,
          height: headSize,
          rotateX: headRotateX,
          rotateY: headRotateY,
          transformStyle: 'preserve-3d',
        }}
      >
        {/* Head base - rounded square robot head */}
        <div
          className="absolute inset-0 rounded-2xl overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f0f23 100%)',
            border: '2px solid rgba(59, 130, 246, 0.3)',
            boxShadow: `
              0 0 20px rgba(59, 130, 246, 0.2),
              inset 0 2px 10px rgba(255, 255, 255, 0.05),
              inset 0 -5px 15px rgba(0, 0, 0, 0.3)
            `,
          }}
        >
          {/* Face plate */}
          <div 
            className="absolute inset-2 rounded-xl"
            style={{
              background: 'linear-gradient(180deg, #1e1e3f 0%, #12122a 100%)',
              border: '1px solid rgba(139, 92, 246, 0.2)',
            }}
          >
            {/* Eyes container */}
            <div className="absolute top-1/3 left-0 right-0 flex justify-center gap-4">
              {/* Left eye */}
              <motion.div
                className="relative"
                style={{
                  width: headSize * 0.2,
                  height: headSize * 0.15,
                  x: eyeOffsetX,
                  y: eyeOffsetY,
                }}
              >
                <div
                  className="w-full h-full rounded-full"
                  style={{
                    background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
                    boxShadow: `
                      0 0 15px rgba(59, 130, 246, 0.6),
                      0 0 30px rgba(139, 92, 246, 0.3),
                      inset 0 2px 4px rgba(255, 255, 255, 0.3)
                    `,
                  }}
                />
                {/* Eye highlight */}
                <div 
                  className="absolute top-1 left-1 w-2 h-2 rounded-full bg-white/60"
                />
              </motion.div>

              {/* Right eye */}
              <motion.div
                className="relative"
                style={{
                  width: headSize * 0.2,
                  height: headSize * 0.15,
                  x: eyeOffsetX,
                  y: eyeOffsetY,
                }}
              >
                <div
                  className="w-full h-full rounded-full"
                  style={{
                    background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
                    boxShadow: `
                      0 0 15px rgba(59, 130, 246, 0.6),
                      0 0 30px rgba(139, 92, 246, 0.3),
                      inset 0 2px 4px rgba(255, 255, 255, 0.3)
                    `,
                  }}
                />
                {/* Eye highlight */}
                <div 
                  className="absolute top-1 left-1 w-2 h-2 rounded-full bg-white/60"
                />
              </motion.div>
            </div>

            {/* Mouth / speaker grille */}
            <div 
              className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1"
              style={{ width: headSize * 0.4 }}
            >
              {[...Array(5)].map((_, i) => (
                <motion.div
                  key={i}
                  className="flex-1 rounded-full"
                  style={{
                    height: 3,
                    background: 'rgba(59, 130, 246, 0.4)',
                  }}
                  animate={{
                    opacity: [0.4, 0.8, 0.4],
                    scaleY: [1, 1.5, 1],
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    delay: i * 0.1,
                    ease: 'easeInOut',
                  }}
                />
              ))}
            </div>
          </div>

          {/* Antenna */}
          <div 
            className="absolute -top-3 left-1/2 -translate-x-1/2 w-2 h-4 rounded-full"
            style={{
              background: 'linear-gradient(180deg, #3b82f6 0%, #1e40af 100%)',
              boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)',
            }}
          >
            <motion.div
              className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full"
              style={{
                background: 'radial-gradient(circle, #60a5fa 0%, #3b82f6 100%)',
                boxShadow: '0 0 12px rgba(59, 130, 246, 0.8)',
              }}
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.8, 1, 0.8],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          </div>

          {/* Side panels (ears) */}
          <div 
            className="absolute top-1/3 -left-2 w-3 h-8 rounded-l-lg"
            style={{
              background: 'linear-gradient(180deg, #1e40af 0%, #1e3a5f 100%)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
            }}
          />
          <div 
            className="absolute top-1/3 -right-2 w-3 h-8 rounded-r-lg"
            style={{
              background: 'linear-gradient(180deg, #1e40af 0%, #1e3a5f 100%)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
            }}
          />
        </div>
      </motion.div>

      {/* NECK - Static */}
      <div
        className="relative z-5"
        style={{
          width: headSize * 0.3,
          height: neckHeight,
          background: 'linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%)',
          borderLeft: '2px solid rgba(59, 130, 246, 0.2)',
          borderRight: '2px solid rgba(59, 130, 246, 0.2)',
        }}
      />

      {/* BODY - Static */}
      <div
        className="relative z-5"
        style={{
          width: headSize * 0.9,
          height: bodyHeight * 0.5,
          marginTop: -2,
          background: 'linear-gradient(180deg, #1a1a2e 0%, #12122a 50%, #0a0a15 100%)',
          borderRadius: '12px 12px 20px 20px',
          border: '2px solid rgba(59, 130, 246, 0.25)',
          boxShadow: `
            0 10px 30px rgba(0, 0, 0, 0.4),
            inset 0 2px 10px rgba(255, 255, 255, 0.02)
          `,
        }}
      >
        {/* Chest plate / core */}
        <div 
          className="absolute top-3 left-1/2 -translate-x-1/2"
          style={{
            width: headSize * 0.35,
            height: headSize * 0.25,
          }}
        >
          <motion.div
            className="w-full h-full rounded-lg"
            style={{
              background: 'radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, rgba(139, 92, 246, 0.1) 70%, transparent 100%)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
            }}
            animate={{
              boxShadow: [
                'inset 0 0 10px rgba(59, 130, 246, 0.3)',
                'inset 0 0 20px rgba(139, 92, 246, 0.5)',
                'inset 0 0 10px rgba(59, 130, 246, 0.3)',
              ],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        </div>

        {/* Shoulder joints */}
        <div 
          className="absolute top-2 -left-2 w-4 h-4 rounded-full"
          style={{
            background: 'linear-gradient(135deg, #1e40af 0%, #1e3a5f 100%)',
            border: '1px solid rgba(59, 130, 246, 0.4)',
            boxShadow: '0 0 8px rgba(59, 130, 246, 0.3)',
          }}
        />
        <div 
          className="absolute top-2 -right-2 w-4 h-4 rounded-full"
          style={{
            background: 'linear-gradient(135deg, #1e40af 0%, #1e3a5f 100%)',
            border: '1px solid rgba(59, 130, 246, 0.4)',
            boxShadow: '0 0 8px rgba(59, 130, 246, 0.3)',
          }}
        />
      </div>

      {/* Ground reflection / shadow */}
      <motion.div
        className="absolute bottom-0 left-1/2 -translate-x-1/2"
        style={{
          width: headSize * 0.8,
          height: 8,
          background: 'radial-gradient(ellipse, rgba(59, 130, 246, 0.2) 0%, transparent 70%)',
          filter: 'blur(4px)',
        }}
        animate={{
          scaleX: [1, 1.1, 1],
          opacity: [0.3, 0.5, 0.3],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </div>
  );
});

export default KuroBot;
