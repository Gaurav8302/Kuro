import React, { memo } from 'react';
import { OptimizedHolographicCard } from '@/components/OptimizedHolographicCard';
import { useOptimizedAnimations } from '@/hooks/use-performance';

interface TypingIndicatorProps {
  isTyping: boolean;
}

/**
 * Isolated typing indicator component.
 * Memoized to prevent parent re-renders from cascading into this component.
 * Also prevents isTyping state changes from triggering message list re-renders.
 */
export const TypingIndicator: React.FC<TypingIndicatorProps> = memo(({ isTyping }) => {
  const { shouldReduceAnimations } = useOptimizedAnimations();

  if (!isTyping) {
    return null;
  }

  return (
    <div className="flex items-center justify-center animate-fade-in-up">
      <OptimizedHolographicCard variant="glow" scanLine={!shouldReduceAnimations} className="px-6 py-4">
        <div className="flex items-center gap-4">
          <div className="flex space-x-2">
            <div className="w-3 h-3 rounded-full bg-holo-cyan-400 shadow-holo-glow animate-typing-dots"></div>
            <div className="w-3 h-3 rounded-full bg-holo-blue-400 shadow-holo-blue animate-typing-dots [animation-delay:0.2s]"></div>
            <div className="w-3 h-3 rounded-full bg-holo-purple-400 shadow-holo-purple animate-typing-dots [animation-delay:0.4s]"></div>
          </div>
          <span className="text-sm text-holo-cyan-300 font-orbitron tracking-wide">KURO IS PROCESSING...</span>
        </div>
      </OptimizedHolographicCard>
    </div>
  );
});

TypingIndicator.displayName = 'TypingIndicator';

export default TypingIndicator;
