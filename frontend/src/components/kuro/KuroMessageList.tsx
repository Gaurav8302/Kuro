import { memo, forwardRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Message } from '@/types';
import { KuroMessageBubble } from './KuroMessageBubble';
import { KuroTypingIndicator } from './KuroTypingIndicator';
import { messageVariants } from '@/utils/animations';

interface KuroMessageListProps {
  messages: Message[];
  userAvatar?: string;
  isTyping?: boolean;
  onRetry?: () => void;
  className?: string;
}

/**
 * KuroMessageList - Professional chat message list
 * Clean, minimal design with subtle animations
 */
export const KuroMessageList = memo(forwardRef<HTMLDivElement, KuroMessageListProps>(
  ({ messages, userAvatar, isTyping, onRetry, className }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'flex-1 overflow-y-auto',
          'px-4 py-6 md:px-6',
          className
        )}
      >
        <div className="max-w-3xl mx-auto space-y-6">
          <AnimatePresence mode="popLayout">
            {messages.map((message, index) => (
              <motion.div
                key={`${message.timestamp}-${index}`}
                variants={messageVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
                layout
              >
                <KuroMessageBubble
                  message={message}
                  userAvatar={userAvatar}
                  onRetry={message.role === 'system' ? onRetry : undefined}
                />
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          <AnimatePresence>
            {isTyping && (
              <motion.div
                variants={messageVariants}
                initial="hidden"
                animate="visible"
                exit="exit"
              >
                <KuroTypingIndicator />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    );
  }
));

KuroMessageList.displayName = 'KuroMessageList';

export default KuroMessageList;
