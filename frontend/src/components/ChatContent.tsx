import React, { memo, ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Message } from '@/types';
import { MessageList } from '@/components/MessageList';
import { HoloSparklesIcon } from '@/components/HolographicIcons';
import { useOptimizedAnimations } from '@/hooks/use-performance';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';

interface ChatContentProps {
  messages: Message[];
  userAvatar: string;
  isTyping: boolean;
  isLoading: boolean;
  onRetry: () => void;
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

/**
 * EmptyState - Shown when no messages exist
 * This is rendered INSIDE the stable chat area, not as a replacement
 */
const EmptyState = memo<{ isLoading: boolean }>(({ isLoading }) => {
  const { shouldReduceAnimations, animationDuration } = useOptimizedAnimations();

  if (isLoading) {
    return (
      <div className="text-center py-16">
        <div className="max-w-md mx-auto">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ 
              duration: shouldReduceAnimations ? 1 : 2, 
              repeat: Infinity, 
              ease: 'linear' 
            }}
            className="w-16 h-16 mx-auto mb-6"
          >
            <div className="w-full h-full rounded-full border-4 border-holo-cyan-400/30 border-t-holo-cyan-400 shadow-holo-glow" />
          </motion.div>
          <h3 className="text-xl font-semibold mb-2 text-holo-cyan-300 text-holo-glow font-orbitron">
            LOADING TRANSMISSION...
          </h3>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center py-16">
      <div className="max-w-lg mx-auto">
        <motion.div
          animate={shouldReduceAnimations ? {} : { 
            scale: [1, 1.1, 1],
            rotate: [0, 5, -5, 0]
          }}
          transition={{ 
            duration: shouldReduceAnimations ? 0 : 4, 
            repeat: shouldReduceAnimations ? 0 : Infinity 
          }}
          className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-holo-cyan-500 to-holo-purple-500 rounded-full flex items-center justify-center shadow-holo-glow"
        >
          <HoloSparklesIcon size={32} className="text-white" />
        </motion.div>
        <h3 className="text-2xl font-semibold mb-4 text-holo-cyan-300 text-holo-glow font-orbitron tracking-wide">
          NEURAL INTERFACE READY
        </h3>
        <p className="text-holo-cyan-100 text-lg mb-3 font-space">
          How may I assist your mission today?
        </p>
        <p className="text-xs text-holo-cyan-400/60 font-orbitron tracking-wider">
          POWERED BY GROQ LLAMA 3 70B NEURAL CORE
        </p>
      </div>
    </div>
  );
});

EmptyState.displayName = 'EmptyState';

/**
 * ChatContent - Handles the CONTENT inside the stable chat area
 * 
 * RULES:
 * - This only changes CONTENT, not the container structure
 * - Parent layout (ChatLayout) remains completely stable
 * - Uses CSS opacity/visibility for transitions, NOT mount/unmount of containers
 */
export const ChatContent: React.FC<ChatContentProps> = memo(({
  messages,
  userAvatar,
  isTyping,
  isLoading,
  onRetry,
  messagesEndRef
}) => {
  const { shouldReduceAnimations } = useOptimizedAnimations();
  const isMobile = useIsMobile();
  const hasMessages = messages.length > 0;

  return (
    <>
      {/* Background effects - always present */}
      {!shouldReduceAnimations && (
        <>
          <div className="absolute inset-0 bg-gradient-to-b from-background/40 to-background/60" />
          <div className="absolute inset-0 holo-grid-bg opacity-20" />
        </>
      )}
      
      {/* Content container - structure never changes */}
      <div className={cn(
        "py-8 space-y-6 relative z-10",
        isMobile && "space-y-3 py-6"
      )}>
        {/* Empty state - visibility controlled, not mount/unmount */}
        <div 
          className={cn(
            "transition-opacity duration-300",
            hasMessages ? "hidden" : "block"
          )}
        >
          <EmptyState isLoading={isLoading && !hasMessages} />
        </div>
        
        {/* Messages list - visibility controlled, not mount/unmount */}
        <div 
          className={cn(
            "transition-opacity duration-300",
            hasMessages ? "block" : "hidden"
          )}
        >
          <MessageList
            messages={messages}
            userAvatar={userAvatar}
            isTyping={isTyping}
            onRetry={onRetry}
          />
        </div>
        
        {/* Scroll anchor - always present */}
        <div ref={messagesEndRef} />
      </div>
    </>
  );
});

ChatContent.displayName = 'ChatContent';

export default ChatContent;
