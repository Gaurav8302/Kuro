import React, { memo, Suspense, lazy } from 'react';
import { motion } from 'framer-motion';
import { Message } from '@/types';
import { MessageList } from '@/components/MessageList';
import { useOptimizedAnimations } from '@/hooks/use-performance';
import { cn } from '@/lib/utils';
import { useIsMobile } from '@/hooks/use-mobile';
import { Sparkles } from 'lucide-react';

// Lazy load the 3D bot for better performance
const KuroBot3D = lazy(() => import('@/components/kuro/KuroBot3D'));

// Fallback while 3D bot loads
const BotFallback = () => (
  <div className="w-64 h-64 flex items-center justify-center">
    <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary to-accent animate-pulse" />
  </div>
);

interface KuroChatContentProps {
  messages: Message[];
  userAvatar: string;
  isTyping: boolean;
  isLoading: boolean;
  onRetry: () => void;
  messagesEndRef: React.RefObject<HTMLDivElement>;
}

/**
 * EmptyState - Professional empty state with 3D Kuro Bot
 * The bot's head follows the cursor
 */
const EmptyState = memo<{ isLoading: boolean }>(({ isLoading }) => {
  const { shouldReduceAnimations } = useOptimizedAnimations();

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
            <div className="w-full h-full rounded-full border-4 border-primary/30 border-t-primary" />
          </motion.div>
          <h3 className="text-xl font-semibold mb-2 text-foreground">
            Loading...
          </h3>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center py-8 px-4">
      <div className="max-w-md mx-auto">
        {/* 3D Kuro Bot with head following cursor */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6 }}
          className="flex justify-center mb-4"
        >
          <Suspense fallback={<BotFallback />}>
            <KuroBot3D className="w-48 h-48 md:w-56 md:h-56" />
          </Suspense>
        </motion.div>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="text-center"
        >
          <h2 className="text-2xl font-bold text-foreground mb-2">
            Hello, I'm Kuro
          </h2>
          <p className="text-muted-foreground mb-6">
            Your personal AI assistant. Ask me anything and I'll help you find answers.
          </p>
          
          {/* Quick action suggestions */}
          <div className="flex flex-wrap justify-center gap-2">
            {["Write code", "Explain concepts", "Creative writing", "Problem solving"].map((action, i) => (
              <motion.div
                key={action}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.5 + i * 0.1 }}
                className="px-4 py-2 rounded-full glass border border-primary/20 text-sm text-foreground flex items-center gap-2 cursor-default"
              >
                <Sparkles className="w-3 h-3 text-primary" />
                {action}
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
});

EmptyState.displayName = 'EmptyState';

/**
 * KuroChatContent - Professional chat content area
 * Clean design with 3D Kuro Bot empty state
 */
export const KuroChatContent: React.FC<KuroChatContentProps> = memo(({
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
    <div className={cn(
      "flex-1 relative overflow-auto",
      "transition-opacity duration-300",
    )}>
      {/* Empty State - shown when no messages */}
      {!hasMessages && (
        <div className="h-full flex items-center justify-center py-12">
          <EmptyState isLoading={isLoading && !hasMessages} />
        </div>
      )}

      {/* Messages Container */}
      {hasMessages && (
        <div className="h-full">
          <MessageList
            messages={messages}
            userAvatar={userAvatar}
            isTyping={isTyping}
            onRetry={onRetry}
          />
          <div ref={messagesEndRef} className="h-4" />
        </div>
      )}
    </div>
  );
});

KuroChatContent.displayName = 'KuroChatContent';

export default KuroChatContent;
