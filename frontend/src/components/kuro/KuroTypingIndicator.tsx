import { memo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';

/**
 * KuroTypingIndicator - Minimal typing dots
 * Clean, professional waveform-like animation
 */
export const KuroTypingIndicator = memo(function KuroTypingIndicator() {
  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <Avatar className="w-8 h-8 flex-shrink-0 border border-white/10">
        <AvatarImage src="/kuroai.png" alt="Kuro" />
        <AvatarFallback className="bg-accent/20 text-accent">
          K
        </AvatarFallback>
      </Avatar>

      {/* Typing indicator */}
      <div
        className={cn(
          'rounded-xl px-4 py-3',
          'glass border border-white/10'
        )}
      >
        <div className="flex items-center gap-1.5 h-5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-muted-foreground"
              animate={{
                y: [-2, 2, -2],
                opacity: [0.4, 1, 0.4],
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: i * 0.15,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
});

export default KuroTypingIndicator;
