import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';
import { useOptimizedAnimations } from '@/hooks/use-performance';

interface OptimizedHolographicCardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'glow' | 'intense';
  hover?: boolean;
  scanLine?: boolean;
}

// Lightweight card for mobile/low-end devices
const LightweightCard: React.FC<OptimizedHolographicCardProps> = memo(({ 
  children, 
  className = '', 
  variant = 'default' 
}) => {
  const variants = {
    default: 'glass-panel border-holo-cyan-500/20',
    glow: 'glass-panel-strong border-holo-cyan-500/30 shadow-holo-glow',
    intense: 'glass-panel-strong border-holo-cyan-500/40 shadow-holo-blue'
  };

  return (
    <div className={cn('relative rounded-xl overflow-hidden transition-all duration-300', variants[variant], className)}>
      {/* Simple CSS-only shimmer effect */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full hover:translate-x-full transition-transform duration-1000 ease-out" />
      </div>
      
      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
});

// Full animated card for desktop
const AnimatedCard: React.FC<OptimizedHolographicCardProps> = memo(({ 
  children, 
  className = '', 
  variant = 'default', 
  hover = true, 
  scanLine = false 
}) => {
  const { animationDuration } = useOptimizedAnimations();
  
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
      transition={{ duration: animationDuration, ease: 'easeOut' }}
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
});

export const OptimizedHolographicCard: React.FC<OptimizedHolographicCardProps> = (props) => {
  const isMobile = useIsMobile();
  const { shouldReduceAnimations } = useOptimizedAnimations();

  // Use lightweight card on mobile or when animations should be reduced
  if (isMobile || shouldReduceAnimations) {
    return <LightweightCard {...props} />;
  }

  // Use full animated card on desktop
  return <AnimatedCard {...props} />;
};

export default OptimizedHolographicCard;