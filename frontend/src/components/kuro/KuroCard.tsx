import { forwardRef, HTMLAttributes } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

interface KuroCardProps extends HTMLMotionProps<'div'> {
  variant?: 'default' | 'elevated' | 'bordered' | 'ghost';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  interactive?: boolean;
}

const variantStyles = {
  default: `
    glass
    border border-white/10
  `,
  elevated: `
    bg-secondary
    border border-white/10
    shadow-lg shadow-black/20
  `,
  bordered: `
    bg-transparent
    border border-border
  `,
  ghost: `
    bg-transparent
    border-none
  `,
};

const paddingStyles = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

/**
 * KuroCard - Professional card component
 * Clean, minimal container with subtle depth
 */
export const KuroCard = forwardRef<HTMLDivElement, KuroCardProps>(
  (
    {
      variant = 'default',
      padding = 'md',
      interactive = false,
      className,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <motion.div
        ref={ref}
        className={cn(
          'rounded-xl',
          'transition-colors duration-150',
          variantStyles[variant],
          paddingStyles[padding],
          interactive && [
            'cursor-pointer',
            'hover:border-white/20',
            'hover:bg-white/5',
          ],
          className
        )}
        whileHover={interactive ? { y: -2 } : undefined}
        whileTap={interactive ? { scale: 0.99 } : undefined}
        transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

KuroCard.displayName = 'KuroCard';

export default KuroCard;
