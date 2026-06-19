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
            var(--kuro-bot-glow-primary) 0%, 
            var(--kuro-bot-glow-accent) 40%,
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
            background: 'linear-gradient(135deg, var(--kuro-bot-body) 0%, var(--kuro-bot-body-dark) 50%, var(--kuro-bot-body-deeper) 100%)',
            border: '2px solid var(--kuro-bot-border-strong)',
            boxShadow: `
              0 0 20px var(--kuro-bot-glow-primary-2),
              inset 0 2px 10px var(--kuro-bot-inset-light),
              inset 0 -5px 15px var(--kuro-bot-inset-dark)
            `,
          }}
        >
          {/* Face plate */}
          <div 
            className="absolute inset-2 rounded-xl"
            style={{
              background: 'linear-gradient(180deg, var(--kuro-bot-face) 0%, var(--kuro-bot-face-deep) 100%)',
              border: '1px solid var(--kuro-bot-glow-accent-2)',
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
                    background: 'linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--accent)) 100%)',
                    boxShadow: `
                      0 0 15px var(--kuro-bot-glow-primary-3),
                      0 0 30px var(--kuro-bot-glow-accent),
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
                    background: 'linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--accent)) 100%)',
                    boxShadow: `
                      0 0 15px var(--kuro-bot-glow-primary-3),
                      0 0 30px var(--kuro-bot-glow-accent),
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
                    background: 'var(--kuro-bot-mouth)',
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
              background: 'linear-gradient(180deg, var(--kuro-bot-antenna-top) 0%, var(--kuro-bot-antenna-bottom) 100%)',
              boxShadow: '0 0 10px var(--kuro-bot-glow-primary-3)',
            }}
          >
            <motion.div
              className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full"
              style={{
                background: 'radial-gradient(circle, var(--kuro-bot-antenna-tip) 0%, var(--kuro-bot-antenna-top) 100%)',
                boxShadow: '0 0 12px var(--kuro-bot-border-strong)',
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
              background: 'var(--kuro-bot-side-panel)',
              border: '1px solid var(--kuro-bot-border-strong)',
            }}
          />
          <div 
            className="absolute top-1/3 -right-2 w-3 h-8 rounded-r-lg"
            style={{
              background: 'var(--kuro-bot-side-panel)',
              border: '1px solid var(--kuro-bot-border-strong)',
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
          background: 'var(--kuro-bot-neck-grad)',
          borderLeft: '2px solid var(--kuro-bot-border)',
          borderRight: '2px solid var(--kuro-bot-border)',
        }}
      />

      {/* BODY - Static */}
      <div
        className="relative z-5"
        style={{
          width: headSize * 0.9,
          height: bodyHeight * 0.5,
          marginTop: -2,
          background: 'var(--kuro-bot-body-grad)',
          borderRadius: '12px 12px 20px 20px',
          border: '2px solid var(--kuro-bot-border-strong)',
          boxShadow: `
            0 10px 30px var(--kuro-bot-shadow),
            inset 0 2px 10px var(--kuro-bot-inset-light)
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
              background: 'var(--kuro-bot-chest-grad)',
              border: '1px solid var(--kuro-bot-border-strong)',
            }}
            animate={{
              boxShadow: [
                'inset 0 0 10px var(--kuro-bot-glow-primary-3)',
                'inset 0 0 20px var(--kuro-bot-glow-accent)',
                'inset 0 0 10px var(--kuro-bot-glow-primary-3)',
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
            background: 'var(--kuro-bot-shoulder)',
            border: '1px solid var(--kuro-bot-border-strong)',
            boxShadow: '0 0 8px var(--kuro-bot-glow-primary-2)',
          }}
        />
        <div 
          className="absolute top-2 -right-2 w-4 h-4 rounded-full"
          style={{
            background: 'var(--kuro-bot-shoulder)',
            border: '1px solid var(--kuro-bot-border-strong)',
            boxShadow: '0 0 8px var(--kuro-bot-glow-primary-2)',
          }}
        />
      </div>

      {/* Ground reflection / shadow */}
      <motion.div
        className="absolute bottom-0 left-1/2 -translate-x-1/2"
        style={{
          width: headSize * 0.8,
          height: 8,
          background: 'radial-gradient(ellipse, var(--kuro-bot-reflection) 0%, transparent 70%)',
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
