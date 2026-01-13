import React, { memo, useMemo } from 'react';
import { Message } from '@/types';
import { OptimizedChatBubble } from '@/components/OptimizedChatBubble';
import { TypingIndicator } from '@/components/TypingIndicator';
import { useOptimizedAnimations } from '@/hooks/use-performance';

interface MessageListProps {
  messages: Message[];
  userAvatar: string;
  isTyping: boolean;
  onRetry: () => void;
}

/**
 * Memoized individual message item to prevent unnecessary re-renders.
 * Only re-renders if the specific message changes.
 */
interface MessageItemProps {
  message: Message;
  index: number;
  userAvatar: string;
  shouldReduceAnimations: boolean;
  onRetry: () => void;
}

const MessageItem = memo<MessageItemProps>(({ 
  message, 
  index, 
  userAvatar, 
  shouldReduceAnimations, 
  onRetry 
}) => (
  <div
    className="transform-gpu animate-fade-in-up"
    style={{ 
      animationDelay: shouldReduceAnimations ? '0ms' : `${Math.min(index * 30, 150)}ms`,
      animationFillMode: 'both'
    }}
  >
    <OptimizedChatBubble
      message={message}
      userAvatar={userAvatar}
      onRetry={onRetry}
    />
  </div>
), (prevProps, nextProps) => {
  // Custom comparison: only re-render if message content changes
  return (
    prevProps.message.message === nextProps.message.message &&
    prevProps.message.timestamp === nextProps.message.timestamp &&
    prevProps.message.role === nextProps.message.role &&
    prevProps.userAvatar === nextProps.userAvatar &&
    prevProps.shouldReduceAnimations === nextProps.shouldReduceAnimations
  );
});

MessageItem.displayName = 'MessageItem';

/**
 * Memoized message list component.
 * Separates message list rendering from typing indicator to prevent
 * isTyping state changes from triggering full list re-renders.
 */
export const MessageList: React.FC<MessageListProps> = memo(({ 
  messages, 
  userAvatar, 
  isTyping, 
  onRetry 
}) => {
  const { shouldReduceAnimations } = useOptimizedAnimations();

  // Memoize the message keys to detect actual message changes
  const messageKeys = useMemo(() => 
    messages.map((m, i) => `${m.timestamp}-${i}`).join(','),
    [messages]
  );

  return (
    <div className="space-y-6">
      {messages.map((message, idx) => (
        <MessageItem
          key={message.timestamp + idx}
          message={message}
          index={idx}
          userAvatar={userAvatar}
          shouldReduceAnimations={shouldReduceAnimations}
          onRetry={onRetry}
        />
      ))}
      <TypingIndicator isTyping={isTyping} />
    </div>
  );
}, (prevProps, nextProps) => {
  // Only re-render if messages array actually changed (by length or content)
  if (prevProps.messages.length !== nextProps.messages.length) return false;
  if (prevProps.userAvatar !== nextProps.userAvatar) return false;
  if (prevProps.isTyping !== nextProps.isTyping) return false;
  
  // Check if last message changed (most common case for new messages)
  const prevLast = prevProps.messages[prevProps.messages.length - 1];
  const nextLast = nextProps.messages[nextProps.messages.length - 1];
  if (prevLast?.message !== nextLast?.message) return false;
  if (prevLast?.timestamp !== nextLast?.timestamp) return false;
  
  return true;
});

MessageList.displayName = 'MessageList';

export default MessageList;
