import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface HolographicButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'ghost';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  glow?: boolean;
  children: React.ReactNode;
}

export const HolographicButton: React.FC<HolographicButtonProps> = ({
  variant = 'primary',
  size = 'md',
  glow = true,
  className,
  children,
  disabled,
  ...props
}) => {
  const variants = {
    primary: 'bg-gradient-to-r from-holo-cyan-500 to-holo-blue-500 text-white border-holo-cyan-400/50',
    secondary: 'bg-gradient-to-r from-holo-purple-500 to-holo-magenta-500 text-white border-holo-purple-400/50',
    accent: 'bg-gradient-to-r from-holo-blue-500 to-holo-cyan-500 text-white border-holo-blue-400/50',
    ghost: 'bg-transparent text-holo-cyan-400 border-holo-cyan-400/30 hover:bg-holo-cyan-500/10'
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
    xl: 'px-8 py-4 text-xl'
  };

  const glowEffects = {
    primary: 'shadow-holo-glow hover:shadow-holo-blue',
    secondary: 'shadow-holo-purple hover:shadow-holo-magenta',
    accent: 'shadow-holo-blue hover:shadow-holo-glow',
    ghost: 'hover:shadow-holo-glow'
  };

  return (
    <motion.button
      className={cn(
        'relative overflow-hidden rounded-lg border font-rajdhani font-medium',
        'transition-all duration-300 ease-out',
        'hover:scale-105 active:scale-95',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100',
        'glass-panel backdrop-blur-md',
        variants[variant],
        sizes[size],
        glow && glowEffects[variant],
        className
      )}
      whileHover={{ 
        scale: disabled ? 1 : 1.05,
        boxShadow: disabled ? undefined : '0 0 30px rgba(0, 230, 214, 0.4)'
      }}
      whileTap={{ scale: disabled ? 1 : 0.95 }}
      disabled={disabled}
      {...props}
    >
      {/* Shimmer effect */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
        initial={{ x: '-100%' }}
        whileHover={{ x: '100%' }}
        transition={{ duration: 0.6, ease: 'easeInOut' }}
      />
      
      {/* Scan line effect */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
          animate={{ x: ['-100%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        />
      </div>
      
      {/* Content */}
      <span className="relative z-10 flex items-center justify-center gap-2">
        {children}
      </span>
    </motion.button>
  );
};

export default HolographicButton;