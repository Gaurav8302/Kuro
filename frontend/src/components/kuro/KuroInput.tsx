import { forwardRef, InputHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface KuroInputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  icon?: React.ReactNode;
}

/**
 * KuroInput - Professional input component
 * Clean, minimal with subtle focus states
 */
export const KuroInput = forwardRef<HTMLInputElement, KuroInputProps>(
  ({ className, error, icon, ...props }, ref) => {
    return (
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </div>
        )}
        <input
          ref={ref}
          className={cn(
            'w-full h-10 px-4 text-sm',
            'glass',
            'text-foreground',
            'placeholder:text-muted-foreground',
            'border border-white/10',
            'rounded-lg',
            'transition-all duration-150',
            'focus:outline-none',
            'focus:border-primary',
            'focus:ring-2 focus:ring-primary/20',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            error && 'border-red-500 focus:border-red-500 focus:ring-red-500/20',
            icon && 'pl-10',
            className
          )}
          {...props}
        />
      </div>
    );
  }
);

KuroInput.displayName = 'KuroInput';

export default KuroInput;
