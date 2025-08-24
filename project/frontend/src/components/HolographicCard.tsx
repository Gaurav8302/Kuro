import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface HolographicCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'glow' | 'intense';
  hover?: boolean;
  scanLine?: boolean;
}

export const HolographicCard: React.FC<HolographicCardProps> = ({
  children,
  className = '',
  variant = 'default',
  hover = true,
  scanLine = false
}) => {
  const variants = {
    default: 'glass-panel border-holo-cyan-500/20',
    glow: 'glass-panel-strong border-holo-cyan-500/30 shadow-holo-glow',
    intense: 'glass-panel-strong holo-border-animated shadow-holo-blue'
  };

  return (
    <motion.div
      className={cn(
        'relative rounded-xl overflow-hidden',
        variants[variant],
        hover && 'hover:shadow-holo-glow hover:border-holo-cyan-500/40',
        className
      )}
      whileHover={hover ? { 
        scale: 1.02,
        boxShadow: '0 0 40px rgba(0, 230, 214, 0.3)'
      } : undefined}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      {/* Scan line effect */}
      {scanLine && (
        <div className="absolute inset-0 overflow-hidden">
          <motion.div
            className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
            animate={{ y: ['0%', '100%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          />
        </div>
      )}
      
      {/* Shimmer effect on hover */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full"
          whileHover={{ x: '200%' }}
          transition={{ duration: 0.8, ease: 'easeInOut' }}
        />
      </div>
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
};

export default HolographicCard;